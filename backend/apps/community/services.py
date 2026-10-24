from io import BytesIO

from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.db.models import Count, Q, Sum
from PIL import Image, ImageOps

from apps.camp import rules
from apps.camp.models import Award, Cohort, DayRecord, Membership, Strike
from apps.camp.services import RuleError, day_progress, local_now, squad_report

try:  # iPhone HEIC/HEIF rasmlarini o'qish uchun (bo'lmasa ham boshqa formatlar ishlaydi)
    from pillow_heif import register_heif_opener
    register_heif_opener()
except Exception:  # noqa: BLE001
    pass


def normalize_image(upload, max_side=1600):
    """Yuklangan rasmni JPEG ga keltiradi (iPhone HEIC ham), EXIF burchagini to'g'rilaydi,
    kattasini kichraytiradi — shunda barcha brauzerlarda ochiladi va joy kam oladi."""
    if upload is None:
        raise RuleError("Rasm tanlanmadi.")
    if getattr(upload, "size", 0) > 25 * 1024 * 1024:
        raise RuleError("Rasm juda katta (25 MB gacha).")
    try:
        img = Image.open(upload)
        img = ImageOps.exif_transpose(img).convert("RGB")
    except Exception:  # noqa: BLE001
        raise RuleError("Bu rasm fayli emas yoki ochib bo'lmadi.")
    img.thumbnail((max_side, max_side))
    buf = BytesIO()
    img.save(buf, "JPEG", quality=85, optimize=True)
    return ContentFile(buf.getvalue(), name="photo.jpg")

from .models import (
    Bounty, BountyCompletion, CoinTransaction, Fire, PhotoChallenge, PhotoEntry, PhotoVote, Reflection, SquadMessage,
)


def add_reflection(membership, text, now=None):
    """Kechki oyna: "Bugungi kun qanday o'tdi?"."""
    now = local_now(now)
    text = (text or "").strip()
    if not text:
        raise RuleError("Javob bo'sh bo'lmasin.")
    limit = rules.current().reflection_max_length
    if len(text) > limit:
        raise RuleError(f"Maksimal {limit} belgi.")
    cohort = membership.cohort
    if not rules.in_window(now, cohort.evening_window_start, cohort.evening_window_end):
        raise RuleError(f"Kechki oyna {cohort.evening_window_start:%H:%M}–{cohort.evening_window_end:%H:%M} da ochiq.")
    reflection, created = Reflection.objects.get_or_create(
        membership=membership, date=now.date(), defaults={"text": text}
    )
    if not created:
        raise RuleError("Bugun javob yozib bo'lgansiz.")
    return reflection


def _visible(membership):
    """Lenta faqat o'z rotasi ichida (rota bo'lmasa — o'z oqimi va jinsi)."""
    if membership.squad_id:
        return Q(membership__squad=membership.squad_id)
    return Q(membership__cohort=membership.cohort, membership__tribe__gender=membership.tribe.gender)


def feed(membership, date):
    """Lenta: rotadoshlarning bugungi refleksiyalari."""
    return (
        Reflection.objects.filter(_visible(membership), date=date)
        .select_related("membership__user")
        .annotate(
            fire_count=Count("fires"),
            fired_by_me=Count("fires", filter=Q(fires__membership=membership)),
        )
    )


def give_fire(membership, reflection: Reflection):
    if not Reflection.objects.filter(_visible(membership), pk=reflection.pk).exists():
        raise RuleError("Bu refleksiya sizga ko'rinmaydi.")
    if reflection.membership_id == membership.pk:
        raise RuleError("O'zingizga olov bera olmaysiz.")
    fire, _ = Fire.objects.get_or_create(reflection=reflection, membership=membership)
    return fire


@transaction.atomic
def complete_bounty(membership, bounty: Bounty, note=""):
    if bounty.cohort_id != membership.cohort_id:
        raise RuleError("Bu topshiriq sizning oqimingizga tegishli emas.")
    if bounty.date != local_now().date():
        raise RuleError("Bu topshiriq faqat o'z kunida bajariladi.")
    try:
        with transaction.atomic():
            completion = BountyCompletion.objects.create(bounty=bounty, membership=membership, note=note[:200])
    except IntegrityError:
        raise RuleError("Bu topshiriqni allaqachon bajargansiz.")
    CoinTransaction.objects.create(
        user=membership.user, amount=bounty.reward,
        reason=CoinTransaction.Reason.BOUNTY, bounty_completion=completion,
    )
    return completion


def coin_balance(user):
    return CoinTransaction.objects.filter(user=user).aggregate(s=Sum("amount"))["s"] or 0


# --- Reyting (ko'p bosqichli) -------------------------------------------------------

POINTS_PER_DAY = 10   # har bajarilgan kun
POINTS_PER_VOTE = 5   # rasm chelenjida olingan har bir 🔥
DONE_STATUSES = ["completed", "rest", "frozen"]


def _ranked_members(membership):
    """Qabila (oqim + jins) a'zolari, ball bilan: bajarilgan kun·10 + IrodaCoin + rasm ovozi·5."""
    members = list(
        Membership.objects.filter(cohort=membership.cohort, tribe__gender=membership.tribe.gender)
        .exclude(status=Membership.Status.EXPELLED)
        .select_related("user", "squad")
        .annotate(days_done=Count("days", filter=Q(days__status__in=DONE_STATUSES), distinct=True))
    )
    uids = [m.user_id for m in members]
    ids = [m.id for m in members]
    coins = dict(CoinTransaction.objects.filter(user_id__in=uids).values_list("user_id").annotate(s=Sum("amount")))
    votes = dict(PhotoVote.objects.filter(entry__membership_id__in=ids).values_list("entry__membership_id").annotate(c=Count("id")))
    rows = []
    for m in members:
        coin = coins.get(m.user_id) or 0
        vote = votes.get(m.id) or 0
        rows.append({
            "id": m.id, "name": m.user.first_name or str(m.user),
            "squad_id": m.squad_id, "squad": m.squad.name if m.squad_id else "—",
            "points": m.days_done * POINTS_PER_DAY + coin + vote * POINTS_PER_VOTE,
            "coins": coin, "votes": vote, "days": m.days_done, "me": m.id == membership.id,
        })
    return rows


def standing(membership):
    """Profil uchun: umumiy ball va o'rin — rota ichida va qabila bo'yicha."""
    rows = sorted(_ranked_members(membership), key=lambda r: -r["points"])
    me = next((r for r in rows if r["me"]), None)
    squad_rows = [r for r in rows if r["squad_id"] == membership.squad_id]
    return {
        "points": me["points"] if me else 0,
        "tribe_rank": rows.index(me) + 1 if me else None,
        "tribe_total": len(rows),
        "squad_rank": squad_rows.index(me) + 1 if me in squad_rows else None,
        "squad_total": len(squad_rows),
    }


def ranking(membership):
    """Uch daraja: rota ichidagi shaxslar, rotalar reytingi, qabila eng zo'rlari."""
    rows = _ranked_members(membership)

    squads = {}
    for r in rows:
        if r["squad_id"] is None:
            continue
        s = squads.setdefault(r["squad_id"], {"squad_id": r["squad_id"], "squad": r["squad"],
                                              "points": 0, "members": 0, "me": r["squad_id"] == membership.squad_id})
        s["points"] += r["points"]
        s["members"] += 1
    squad_list = sorted(squads.values(), key=lambda s: -s["points"] / max(s["members"], 1))
    for i, s in enumerate(squad_list, 1):
        s["rank"] = i
        s["avg"] = round(s["points"] / max(s["members"], 1), 1)

    my_squad = sorted([r for r in rows if r["squad_id"] == membership.squad_id], key=lambda r: -r["points"])
    tribe_top = sorted(rows, key=lambda r: -r["points"])[:20]
    return {
        "my_squad_name": membership.squad.name if membership.squad_id else None,
        "squad": my_squad,
        "squads": squad_list,
        "tribe_top": tribe_top,
    }


# --- Tonggi rasm chelenji -----------------------------------------------------------

def todays_challenge(cohort, date):
    challenge, _ = PhotoChallenge.objects.get_or_create(cohort=cohort, date=date)
    return challenge


def photo_feed(membership, now=None):
    """Bugungi rasm chelenji: o'z qabilasidagi rasmlar, ovoz bo'yicha tartiblangan."""
    now = local_now(now)
    challenge = todays_challenge(membership.cohort, now.date())
    entries = (
        PhotoEntry.objects.filter(challenge=challenge, membership__tribe__gender=membership.tribe.gender)
        .select_related("membership__user")
        .annotate(nvotes=Count("votes", distinct=True),
                  mine=Count("votes", filter=Q(votes__voter=membership), distinct=True))
    )
    rows = sorted([
        {
            "id": e.id, "author": e.membership.user.first_name or "Ishtirokchi",
            "me": e.membership_id == membership.id, "votes": e.nvotes, "voted_by_me": bool(e.mine),
        }
        for e in entries
    ], key=lambda r: (-r["votes"], r["id"]))
    for i, r in enumerate(rows):
        r["rank"] = i + 1
    my_count = sum(1 for e in entries if e.membership_id == membership.id)
    return {
        "title": challenge.title, "theme": challenge.theme, "max": challenge.max_entries,
        "my_count": my_count, "can_add": my_count < challenge.max_entries, "entries": rows,
    }


def upload_photo(membership, image, now=None):
    now = local_now(now)
    if image is None:
        raise RuleError("Rasm tanlanmadi.")
    if getattr(image, "size", 0) > 10 * 1024 * 1024:
        raise RuleError("Rasm juda katta (10 MB gacha).")
    challenge = todays_challenge(membership.cohort, now.date())
    count = PhotoEntry.objects.filter(challenge=challenge, membership=membership).count()
    if count >= challenge.max_entries:
        raise RuleError(f"Bugun {challenge.max_entries} tagacha rasm yuborish mumkin.")
    return PhotoEntry.objects.create(challenge=challenge, membership=membership, image=image)


def vote_photo(membership, entry):
    """🔥 ovoz — o'ziga emas, faqat o'z qabilasidagi rasmga. Qayta bosilsa — ovoz olinadi."""
    if entry.membership_id == membership.id:
        raise RuleError("O'z rasmingizga ovoz bera olmaysiz.")
    if entry.membership.tribe.gender != membership.tribe.gender or entry.challenge.cohort_id != membership.cohort_id:
        raise RuleError("Bu rasm sizga ko'rinmaydi.")
    existing = PhotoVote.objects.filter(entry=entry, voter=membership).first()
    if existing:
        existing.delete()
        return False
    try:
        PhotoVote.objects.create(entry=entry, voter=membership)
    except IntegrityError:
        pass
    return True


# --- Rota chati (Mini App ichida) ---------------------------------------------------

def window_state(cohort, now):
    """Rota chati holati: hozir qaysi oyna ochiq, ochiq bo'lmasa — keyingisi qachon ochiladi."""
    # Oqim hali boshlanmagan (qabul davri) — chat erkin ochiq, rotadoshlar tanishib oladi.
    if cohort.status != Cohort.Status.RUNNING:
        return {"open": True, "which": "prestart", "label": "Start oldidan", "closes_at": None}
    windows = [
        ("morning", "Tonggi oyna", cohort.morning_window_start, cohort.morning_window_end),
        ("evening", "Kechki oyna", cohort.evening_window_start, cohort.evening_window_end),
    ]
    t = now.time()
    for key, label, start, end in windows:
        if start <= t <= end:
            return {"open": True, "which": key, "label": label, "closes_at": end.strftime("%H:%M")}
    upcoming = sorted((start for _, _, start, _ in windows if start > t))
    if upcoming:
        nxt, nxt_label = upcoming[0], next(lb for _, lb, s, _ in windows if s == upcoming[0])
    else:  # bugun ikkala oyna ham o'tdi — ertalabki oyna ertaga
        nxt, nxt_label = cohort.morning_window_start, "Tonggi oyna"
    return {"open": False, "which": None, "label": nxt_label, "next_open": nxt.strftime("%H:%M")}


def _avatar(user):
    return user.id if user.avatar else None


def _voice_item(record, viewer):
    """1-topshiriq: ovozli raport kartasi."""
    m = record.membership
    return {
        "type": "report", "kind": "voice",
        "at": (record.voice_at or record.woke_at).isoformat() if (record.voice_at or record.woke_at) else None,
        "author": m.user.first_name or str(m.user), "me": m.user_id == viewer.user_id, "avatar": _avatar(m.user),
        "status": "late" if record.voice_late else "accepted", "late": record.voice_late,
        "admin_reviewed": bool(record.admin_reviewed_at),
        "phrase": record.phrase, "day_number": record.day_number,
        "media": {"kind": "voice", "id": record.id} if record.voice_file_id else None,
    }


def _video_item(record, video, viewer):
    """3-topshiriq: yurish videosi kartasi — rotadosh tekshiruvchi bo'lsa tasdiq/rad tugmalari bilan."""
    m = record.membership
    my_review = next((r for r in video.reviews.all() if r.reviewer_id == viewer.id), None)
    return {
        "type": "report", "kind": "video",
        "at": (video.uploaded_at or record.woke_at).isoformat(),
        "author": m.user.first_name or str(m.user), "me": m.user_id == viewer.user_id, "avatar": _avatar(m.user),
        "status": {"approved": "peer_approved", "rejected": "peer_rejected"}.get(video.status, "pending"),
        "late": False, "admin_reviewed": bool(video.admin_reviewed_at),
        "phrase": record.phrase, "day_number": record.day_number,
        "media": {"kind": "video", "id": video.id},
        "proof_id": video.id,
        # Menga tekshirish topshirilgan va hali ovoz bermaganman (o'zimnikini baholay olmayman)
        "can_review": bool(my_review) and my_review.approved is None and m.user_id != viewer.user_id,
        "my_vote": my_review.approved if my_review else None,
    }


def squad_chat(membership, now=None):
    """Rota chati lentasi: raportlar, ogohlantirishlar, bosqichlar va matn xabarlari — vaqt tartibida."""
    now = local_now(now)
    squad = membership.squad
    if squad is None:
        raise RuleError("Siz hali rotaga biriktirilmagansiz.")
    date = now.date()
    viewer_id = membership.user_id
    items = []

    # Chatda haqiqiy raportlar: ovoz va video alohida kartalar. Faqat uyg'onganlar — safda, karta emas.
    for record in (
        DayRecord.objects.filter(membership__squad=squad, date=date)
        .filter(Q(voice_at__isnull=False) | Q(video__isnull=False))
        .select_related("membership__user", "video")
        .prefetch_related("video__reviews")
    ):
        if record.voice_at:
            items.append(_voice_item(record, membership))
        video = getattr(record, "video", None)
        if video:
            items.append(_video_item(record, video, membership))

    # 2-topshiriq: iliq suv rasmlari — rotadoshlar ko'radi
    for record in (
        DayRecord.objects.filter(membership__squad=squad, date=date, water_at__isnull=False)
        .select_related("membership__user")
    ):
        u = record.membership.user
        items.append({"type": "water", "at": record.water_at.isoformat(), "id": record.id,
                      "author": u.first_name or str(u), "me": u.id == viewer_id, "avatar": _avatar(u)})

    for s in (
        Strike.objects.filter(membership__squad=squad, created_at__date=date, revoked=False,
                              cancelled_by_immunity=False)
        .select_related("membership__user")
    ):
        name = s.membership.user.first_name or str(s.membership.user)
        items.append({"type": "strike", "at": s.created_at.isoformat(), "author": name,
                      "reason": s.get_reason_display()})

    for a in (
        Award.objects.filter(membership__squad=squad, issued_at__date=date)
        .select_related("membership__user", "stage")
    ):
        name = a.membership.user.first_name or str(a.membership.user)
        items.append({"type": "award", "at": a.issued_at.isoformat(), "author": name,
                      "stage": a.stage.name, "day": a.stage.day, "icon": a.stage.icon})

    for msg in (
        SquadMessage.objects.filter(squad=squad, created_at__date=date).select_related("author__user", "mentor")
    ):
        if msg.mentor_id or not msg.author:
            items.append({"type": "message", "at": msg.created_at.isoformat(), "author": mentor_name(msg.mentor),
                          "me": False, "mentor": True, "text": msg.text,
                          "avatar": _avatar(msg.mentor) if msg.mentor else None})
            continue
        author = msg.author.user.first_name or "Ishtirokchi"
        items.append({"type": "message", "at": msg.created_at.isoformat(), "author": author,
                      "me": msg.author.user_id == viewer_id, "text": msg.text, "avatar": _avatar(msg.author.user)})

    # Kechki refleksiya ham chatda — 🔥 bilan
    reflections = (
        Reflection.objects.filter(membership__squad=squad, date=date)
        .select_related("membership__user")
        .annotate(fire_count=Count("fires", distinct=True),
                  mine_fire=Count("fires", filter=Q(fires__membership=membership), distinct=True))
    )
    my_reflected = False
    for r in reflections:
        mine = r.membership_id == membership.id
        my_reflected = my_reflected or mine
        items.append({
            "type": "reflection", "at": r.created_at.isoformat(), "id": r.id,
            "author": r.membership.user.first_name or "Ishtirokchi", "me": mine,
            "text": r.text, "fires": r.fire_count, "fired_by_me": bool(r.mine_fire),
        })

    items.sort(key=lambda x: x["at"] or "")
    window = window_state(membership.cohort, now)
    if membership.cohort.status == Cohort.Status.RUNNING:
        report = squad_report(squad, date)
        day_number = report["day_number"]
        roll = {"done": report["done"], "total": report["total"]}
    else:  # start oldidan — kun raqami yo'q, safda butun rota
        day_number = 0
        roll = {"done": 0, "total": squad.memberships.filter(status=Membership.Status.ACTIVE).count()}
    return {
        "squad": squad.name,
        "tribe": str(squad.tribe),
        "day_number": day_number,
        "prestart": window.get("which") == "prestart",
        "window": window,
        "roll": roll,
        "items": items,
        # Kechki oyna ochiq va bugun refleksiya yozmagan bo'lsa — ilova taklif qiladi
        "can_reflect": window.get("which") == "evening" and not my_reflected,
    }


def post_chat_message(membership, text, now=None):
    """Chatga matn yozish — faqat oyna ochiq bo'lganda."""
    now = local_now(now)
    text = (text or "").strip()
    if not text:
        raise RuleError("Xabar bo'sh bo'lmasin.")
    if membership.squad_id is None:
        raise RuleError("Siz hali rotaga biriktirilmagansiz.")
    if not window_state(membership.cohort, now)["open"]:
        raise RuleError("Hozir oyna yopiq — faqat kuzatish mumkin. Chat belgilangan vaqtda ochiladi.")
    return SquadMessage.objects.create(squad_id=membership.squad_id, author=membership, text=text[:1000])


def mentor_name(user):
    name = (user.first_name if user else "") or ""
    return f"Mentor · {name}" if name else "Mentor"


def post_mentor_message(squad, admin, text):
    """Admin (mentor) rota chatiga yozadi — oyna cheklovi yo'q."""
    text = (text or "").strip()
    if not text:
        raise RuleError("Xabar bo'sh bo'lmasin.")
    return SquadMessage.objects.create(squad=squad, mentor=admin, text=text[:1000])
