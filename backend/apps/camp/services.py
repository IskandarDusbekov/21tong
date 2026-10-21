"""
Lagerning asosiy biznes-logikasi. Bot ham, Mini App ham faqat shu funksiyalar orqali
holatni o'zgartiradi — qoidalar bir joyda.
"""
import datetime as dt
from dataclasses import dataclass

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from apps.accounts.models import Gender, Region, User

from . import rules
from .models import (
    Award, Cohort, DayRecord, Freeze, Immunity, Membership, Notification, Squad, Strike, Tribe, WakeSlot,
)


class RuleError(Exception):
    """Qoida buzilganda — xabar foydalanuvchiga ko'rsatiladi."""


def notify(user, kind, **payload):
    return Notification.objects.create(user=user, kind=kind, payload=payload)


def local_now(now=None):
    return timezone.localtime(now or timezone.now())


# --- Onboarding ---------------------------------------------------------------

def days_until(date, today=None):
    return (date - (today or local_now().date())).days


def slot_json(slot, today=None):
    c = slot.cohort
    return {
        "id": slot.id,
        "label": str(slot),
        "title": slot.title,
        "start_wake_time": slot.start_wake_time.strftime("%H:%M"),
        "target_wake_time": slot.target_wake_time.strftime("%H:%M"),
        "cohort": {"id": c.id, "name": c.name, "start_date": c.start_date.isoformat(),
                   "start_label": c.start_date.strftime("%d.%m.%Y"), "days_left": days_until(c.start_date, today)},
    }


def open_slots():
    """Arizada tanlash mumkin bo'lgan tayyor rota vaqtlari (qabul ochiq oqimlarda)."""
    return list(
        WakeSlot.objects.filter(is_open=True, cohort__status=Cohort.Status.RECRUITING)
        .select_related("cohort").order_by("cohort__start_date", "start_wake_time")
    )


def _clean_name(value, field):
    value = " ".join((value or "").split())
    if not 2 <= len(value) <= 30:
        raise RuleError(f"{field} 2–30 ta harfdan iborat bo'lsin.")
    return value


@transaction.atomic
def register_user(*, telegram_id, gender, goal, username="", first_name="", last_name="", region="",
                  slot_id=None, referral_code=None, current_wake_time=None, target_wake_time=None):
    """Botdagi ariza yakunlanganda chaqiriladi. Jins keyin o'zgarmaydi. Adminlarga xabar ketadi."""
    if gender not in Gender.values:
        raise RuleError("Jins noto'g'ri ko'rsatilgan.")
    if region and region not in Region.values:
        raise RuleError("Viloyat noto'g'ri tanlangan.")
    if not rules.current().registration_open and not User.objects.filter(telegram_id=telegram_id).exists():
        raise RuleError("Hozircha ariza qabul qilinmayapti.")
    slot = None
    if slot_id:
        slot = WakeSlot.objects.select_related("cohort").filter(
            pk=slot_id, is_open=True, cohort__status=Cohort.Status.RECRUITING
        ).first()
        if slot is None:
            raise RuleError("Bu rotaga qabul yopilgan. Boshqasini tanlang.")
        current_wake_time, target_wake_time = slot.start_wake_time, slot.target_wake_time
    if current_wake_time and target_wake_time and target_wake_time > current_wake_time:
        raise RuleError("Maqsad vaqti hozirgi vaqtdan kech bo'lmasin — biz erta turishga o'rganamiz.")

    user, created = User.objects.get_or_create(
        telegram_id=telegram_id, defaults={"username": f"tg{telegram_id}", "telegram_username": username},
    )
    if user.gender and user.gender != gender:
        raise RuleError("Jinsni o'zgartirib bo'lmaydi.")
    if user.status in (User.Status.APPROVED, User.Status.REJECTED):
        return user

    user.gender = gender
    user.goal = goal.strip()
    user.telegram_username = username or user.telegram_username
    if first_name:
        user.first_name = _clean_name(first_name, "Ism")
    if last_name:
        user.last_name = _clean_name(last_name, "Familiya")
    user.region = region or user.region
    user.preferred_slot = slot or user.preferred_slot
    user.current_wake_time = current_wake_time or user.current_wake_time
    user.target_wake_time = target_wake_time or user.target_wake_time
    was_pending = user.status == User.Status.PENDING
    user.status = User.Status.PENDING
    if referral_code and not user.referred_by_id:
        referrer = User.objects.filter(referral_code=referral_code).exclude(pk=user.pk).first()
        user.referred_by = referrer
    user.save()
    if not was_pending:
        notify(user, Notification.Kind.NEW_APPLICATION, **application_payload(user))
    return user


def application_payload(user):
    fmt = lambda t: t.strftime("%H:%M") if t else None  # noqa: E731
    return {
        "name": user.display_name,
        "username": user.telegram_username,
        "gender": user.gender,
        "region": user.get_region_display() if user.region else None,
        "goal": user.goal,
        "slot": str(user.preferred_slot) if user.preferred_slot_id else None,
        "current_wake_time": fmt(user.current_wake_time),
        "target_wake_time": fmt(user.target_wake_time),
        "referred_by": str(user.referred_by) if user.referred_by_id else None,
    }


def placement_payload(m):
    """Qabul qilingan odamga: oqim, start, rota, birinchi budilnik."""
    c = m.cohort
    return {
        "name": m.user.first_name or m.user.display_name,
        "cohort": c.name,
        "start_date": c.start_date.strftime("%d.%m.%Y"),
        "days_left": max(days_until(c.start_date), 0),
        "tribe": str(m.tribe),
        "squad": m.squad.name if m.squad_id else "—",
        "alarm": m.tribe.start_wake_time.strftime("%H:%M"),
        "target": m.target_wake_time.strftime("%H:%M"),
        "invite_link": m.squad.invite_link if m.squad_id else "",
    }


def join_slot(user, slot):
    return join_cohort(user, slot.cohort, slot.start_wake_time, slot.target_wake_time)


@transaction.atomic
def approve_user(user):
    """
    Admin tasdiqlaydi. Arizada tanlangan tayyor rotaga (yoki qabul ochiq oqimga arizadagi vaqtlar bilan)
    darhol joylashtiriladi. Sozlamada yoqilgan bo'lsa, taklif qilgan do'stga bir marta Immunitet.
    """
    if user.status != User.Status.PENDING:
        return False
    user.status = User.Status.APPROVED
    user.approved_at = timezone.now()
    user.save(update_fields=["status", "approved_at"])

    m = None
    slot = user.preferred_slot
    try:
        if slot and slot.cohort.status == Cohort.Status.RECRUITING:
            m = join_slot(user, slot)
        else:
            cohort = Cohort.objects.filter(status=Cohort.Status.RECRUITING).order_by("start_date").first()
            if cohort and user.current_wake_time and user.target_wake_time:
                m = join_cohort(user, cohort, user.current_wake_time, user.target_wake_time)
    except RuleError:
        m = None
    notify(user, Notification.Kind.APPROVED, **(placement_payload(m) if m else {}))

    # Shartli UPDATE — parallel tasdiqlarda ham Immunitet faqat bir marta beriladi
    if user.referred_by_id and rules.current().referral_immunity:
        granted = User.objects.filter(pk=user.referred_by_id, referral_immunity_granted=False).update(
            referral_immunity_granted=True
        )
        if granted:
            grant_immunity(User.objects.get(pk=user.referred_by_id), Immunity.Source.REFERRAL)
    return True


def grant_immunity(user, source):
    immunity = Immunity.objects.create(user=user, source=source)
    notify(user, Notification.Kind.IMMUNITY_GRANTED, source=source)
    return immunity


def reject_user(user):
    if user.status != User.Status.PENDING:
        return False
    user.status = User.Status.REJECTED
    user.save(update_fields=["status"])
    notify(user, Notification.Kind.REJECTED)
    return True


@transaction.atomic
def join_cohort(user, cohort: Cohort, start_wake_time: dt.time, target_wake_time: dt.time):
    """Foydalanuvchini o'z jinsidagi va vaqtidagi qabilaga joylashtiradi."""
    if user.status != User.Status.APPROVED:
        raise RuleError("Avval admin tasdig'idan o'tishingiz kerak.")
    if not user.gender:
        raise RuleError("Jins ko'rsatilmagan.")
    if cohort.status != Cohort.Status.RECRUITING:
        raise RuleError("Bu oqimga qabul yopilgan.")
    if target_wake_time > start_wake_time:
        raise RuleError("Maqsad vaqti boshlang'ich vaqtdan kech bo'lishi mumkin emas.")
    tribe, _ = Tribe.objects.get_or_create(cohort=cohort, gender=user.gender, start_wake_time=start_wake_time)
    if Membership.objects.filter(user=user, cohort=cohort).exists():
        raise RuleError("Siz bu oqimga allaqachon qo'shilgansiz.")
    return Membership.objects.create(
        user=user, cohort=cohort, tribe=tribe, squad=assign_squad(tribe), target_wake_time=target_wake_time
    )


def assign_squad(tribe):
    """Bo'sh joyi bor birinchi rota; hammasi to'lgan bo'lsa — yangi rota ochiladi."""
    squads = (
        Squad.objects.filter(tribe=tribe)
        .annotate(size=Count("memberships", filter=Q(memberships__status=Membership.Status.ACTIVE)))
        .order_by("number")
    )
    for squad in squads:
        if squad.size < rules.current().squad_size:
            return squad
    last = max((s.number for s in squads), default=0)
    return Squad.objects.create(tribe=tribe, number=last + 1)


# --- Kunlik zanjir ------------------------------------------------------------

def active_membership(user):
    return (
        Membership.objects.select_related("cohort", "tribe", "squad", "user")
        .filter(user=user, status=Membership.Status.ACTIVE, cohort__status=Cohort.Status.RUNNING)
        .first()
    )


def ensure_day_record(membership: Membership, date: dt.date):
    day_number = membership.cohort.day_number(date)
    if day_number is None:
        raise RuleError("Bugun oqim kunlariga kirmaydi.")
    alarm = rules.alarm_time_for_day(membership.tribe.start_wake_time, membership.target_wake_time, day_number)
    record, _ = DayRecord.objects.get_or_create(
        membership=membership, date=date, defaults={"day_number": day_number, "alarm_time": alarm}
    )
    if record.status == DayRecord.Status.PENDING and membership.freezes.filter(date=date).exists():
        record.status = DayRecord.Status.FROZEN
        record.save(update_fields=["status"])
    return record


def _today_record(membership, now):
    record = ensure_day_record(membership, now.date())
    if record.status == DayRecord.Status.FROZEN:
        raise RuleError("Bugun muzlatilgan kun — dam oling.")
    if record.status != DayRecord.Status.PENDING:
        raise RuleError("Bugungi kun allaqachon yakunlangan.")
    return record


def press_wake(membership, now=None):
    """1-qadam: "Uyg'ondim" (bot tugmasi yoki Mini App). Bugungi o'qiladigan gap beriladi."""
    now = local_now(now)
    record = _today_record(membership, now)
    if record.woke_at:
        return record
    earliest = dt.datetime.combine(now.date(), membership.cohort.morning_window_start, tzinfo=now.tzinfo)
    earliest = min(earliest, dt.datetime.combine(now.date(), record.alarm_time, tzinfo=now.tzinfo))
    if now < earliest - dt.timedelta(hours=1):
        raise RuleError("Hali juda erta. Budilnik vaqtiga yaqin bosing.")
    record.woke_at = now
    record.phrase = rules.random_phrase()
    record.save(update_fields=["woke_at", "phrase"])
    return record


def proof_record(membership, now):
    """Raport qabul qilishdan oldingi umumiy tekshiruvlar."""
    record = _today_record(membership, now)
    if not record.woke_at:
        raise RuleError("Avval «Uyg'ondim» tugmasini bosing — keyin o'qiladigan gap beriladi.")
    if now > rules.proof_deadline(record.date, record.alarm_time, now.tzinfo, record.day_number):
        raise RuleError(
            f"Kechikding. Raport budilnikdan keyin {rules.proof_minutes(record.day_number)} daqiqa ichida "
            "yuborilishi kerak edi."
        )
    return record


def record_voice(membership, file_id="", now=None):
    """Ovozli raport: bot bergan gap o'qilgan voice — botga shaxsiy yuboriladi."""
    now = local_now(now)
    record = proof_record(membership, now)
    if rules.video_required(record.day_number):
        raise RuleError(
            f"{rules.current().video_from_day}-kundan boshlab ovoz emas — tashqarida yozilgan video krujok kerak."
        )
    if record.voice_at:
        raise RuleError("Bugungi ovozli raport allaqachon qabul qilingan.")
    record.voice_at = now
    record.voice_file_id = file_id
    record.save(update_fields=["voice_at", "voice_file_id"])
    return record


def proof_kind(day_number):
    return rules.proof_kind(day_number)


def day_progress(record: DayRecord):
    video = getattr(record, "video", None)
    tz = timezone.get_current_timezone()
    kind = proof_kind(record.day_number)
    deadline = rules.proof_deadline(record.date, record.alarm_time, tz, record.day_number)
    return {
        "date": record.date.isoformat(),
        "day_number": record.day_number,
        "alarm_time": record.alarm_time.strftime("%H:%M"),
        "status": record.status,
        "woke": bool(record.woke_at),
        "phrase": record.phrase,
        "proof_kind": kind,
        "proof_deadline": timezone.localtime(deadline).strftime("%H:%M"),
        "proof_minutes": rules.proof_minutes(record.day_number),
        "voice": bool(record.voice_at),
        "video_required": kind == "video",
        "video": video.status if video else None,
        "proof_done": bool(record.voice_at) if kind == "voice" else (video is not None and video.status != "rejected"),
    }


def survived_days(membership):
    return membership.days.exclude(status__in=[DayRecord.Status.PENDING, DayRecord.Status.FAILED]).count()


def journey(membership, now=None):
    """Mini App'dagi "Yo'l" ekrani uchun: bosqichlar, 21 kunlik kalendar, oynalar."""
    now = local_now(now)
    cohort = membership.cohort
    survived = survived_days(membership)
    records = {r.day_number: r for r in membership.days.all()}
    start, target = membership.tribe.start_wake_time, membership.target_wake_time

    c = rules.current()
    days = []
    for n in range(1, cohort.duration_days + 1):
        date = cohort.start_date + dt.timedelta(days=n - 1)
        record = records.get(n)
        if record:
            status = record.status
        else:
            status = "future" if date > now.date() else DayRecord.Status.PENDING
        days.append({
            "day_number": n,
            "date": date.isoformat(),
            "weekday": date.weekday(),
            "status": status,
            "today": date == now.date(),
            "alarm_time": (record.alarm_time if record else rules.alarm_time_for_day(start, target, n, c)).strftime("%H:%M"),
            "video_required": rules.video_required(n, c),
        })

    stages = [{**s, "reached": survived >= s["day"]} for s in rules.stages()]
    next_stage = next((s for s in stages if not s["reached"]), None)

    def window(start_t, end_t):
        return {
            "start": start_t.strftime("%H:%M"),
            "end": end_t.strftime("%H:%M"),
            "open": rules.in_window(now, start_t, end_t),
        }

    tomorrow_number = cohort.day_number(now.date() + dt.timedelta(days=1))
    return {
        "survived": survived,
        "current_day": cohort.day_number(now.date()),
        "duration": cohort.duration_days,
        "stage": rules.stage_for(survived, stages),
        "next_stage": next_stage,
        "stages": stages,
        "days": days,
        "windows": {
            "morning": window(cohort.morning_window_start, cohort.morning_window_end),
            "evening": window(cohort.evening_window_start, cohort.evening_window_end),
        },
        "tomorrow_alarm": (
            rules.alarm_time_for_day(start, target, tomorrow_number, c).strftime("%H:%M") if tomorrow_number else None
        ),
        "rules": {
            "shift_from_day": c.shift_from_day,
            "video_from_day": c.video_from_day,
            "shift_minutes": c.shift_step_minutes,
            "grace_minutes": c.wake_grace_minutes,
            "voice_deadline_minutes": c.voice_deadline_minutes,
            "video_deadline_minutes": c.video_deadline_minutes,
            "max_strikes": c.max_strikes,
            "squad_size": c.squad_size,
            "freezes_left": freezes_left(membership, c),
        },
    }


# --- Ogohlantirish / Immunitet ---------------------------------------------------

@dataclass
class StrikeResult:
    strike: Strike
    immunity_used: bool
    expelled: bool


def _squad_payload(membership):
    """Rota guruhiga ham e'lon qilinadi — lagerda hamma bir-biri uchun javobgar."""
    return {
        "name": membership.user.first_name or str(membership.user),
        "squad_chat_id": membership.squad.telegram_chat_id if membership.squad_id else None,
    }


@transaction.atomic
def issue_strike(membership, reason, day=None, use_immunity=True):
    strike = Strike.objects.create(membership=membership, reason=reason, day=day)
    immunity = (
        Immunity.objects.select_for_update().filter(user=membership.user, used_on__isnull=True).first()
        if use_immunity else None
    )
    if immunity:
        immunity.used_on = strike
        immunity.save(update_fields=["used_on"])
        strike.cancelled_by_immunity = True
        strike.save(update_fields=["cancelled_by_immunity"])
        notify(membership.user, Notification.Kind.IMMUNITY_USED, reason=reason)
        return StrikeResult(strike, immunity_used=True, expelled=False)

    max_strikes = rules.current().max_strikes
    count = membership.active_strikes
    squad = _squad_payload(membership)
    notify(membership.user, Notification.Kind.STRIKE, reason=reason, count=count, max=max_strikes, **squad)
    if count >= max_strikes:
        expel(membership)
        return StrikeResult(strike, immunity_used=False, expelled=True)
    return StrikeResult(strike, immunity_used=False, expelled=False)


def expel(membership, notify_user=True):
    membership.status = Membership.Status.EXPELLED
    membership.left_at = timezone.now()
    membership.save(update_fields=["status", "left_at"])
    if notify_user:
        notify(membership.user, Notification.Kind.EXPELLED, **_squad_payload(membership))


def restore(membership):
    """Admin: chiqarilgan ishtirokchini qaytarish."""
    membership.status = Membership.Status.ACTIVE
    membership.left_at = None
    membership.save(update_fields=["status", "left_at"])


def revoke_strike(strike):
    """Admin: ogohlantirishni bekor qilish (sanoqdan chiqadi)."""
    if not strike.revoked:
        strike.revoked = True
        strike.save(update_fields=["revoked"])


def excuse_day(record):
    """Admin: kunni uzrli deb bajarilgan qilish va shu kun uchun berilgan ogohlantirishni bekor qilish."""
    record.status = DayRecord.Status.COMPLETED
    record.evaluated_at = record.evaluated_at or timezone.now()
    record.save(update_fields=["status", "evaluated_at"])
    for strike in record.strikes.filter(revoked=False):
        revoke_strike(strike)


def _failure_reason(record: DayRecord, tz):
    if not record.woke_at or record.woke_at > rules.wake_deadline(record.date, record.alarm_time, tz):
        return Strike.Reason.LATE
    if not rules.video_required(record.day_number):
        return None if record.voice_at else Strike.Reason.NO_VOICE
    video = getattr(record, "video", None)
    if video is None:
        return Strike.Reason.NO_VIDEO
    if video.status == video.Status.REJECTED:
        return Strike.Reason.REJECTED
    # Hech kim ovoz bermagan video: sozlamaga qarab tasdiqlangan yoki rad etilgan hisoblanadi
    if video.status == video.Status.REVIEWING and not rules.current().unreviewed_counts_as_approved:
        return Strike.Reason.REJECTED
    return None


@transaction.atomic
def evaluate_day(record: DayRecord):
    """Kun yakunida chaqiriladi: ogohlantirish, Immunitet va bosqichni hal qiladi. Idempotent."""
    record = DayRecord.objects.select_for_update().select_related("membership__cohort", "membership__user").get(pk=record.pk)
    membership = record.membership
    if record.status != DayRecord.Status.PENDING or membership.status != Membership.Status.ACTIVE:
        return record

    tz = timezone.get_current_timezone()
    reason = _failure_reason(record, tz)
    if rules.is_rest_day(record.date):
        if reason is None:
            record.status = DayRecord.Status.COMPLETED
            if rules.current().sunday_immunity:
                grant_immunity(membership.user, Immunity.Source.SUNDAY)
        else:
            record.status = DayRecord.Status.REST
    elif reason is None:
        record.status = DayRecord.Status.COMPLETED
    else:
        record.status = DayRecord.Status.FAILED

    record.evaluated_at = timezone.now()
    record.save(update_fields=["status", "evaluated_at"])

    if record.status == DayRecord.Status.FAILED:
        issue_strike(membership, reason, day=record)
    else:
        survived = survived_days(membership)
        stage = rules.stage_for(survived)
        if stage and stage["day"] == survived:
            grant_award(membership, stage)
    return record


def grant_award(membership, stage):
    """Bosqich mukofoti (pogon/medal/sertifikat) — bir bosqichga bir marta. Bot rasmini yuboradi."""
    award, created = Award.objects.get_or_create(membership=membership, stage_id=stage["id"])
    if created:
        notify(
            membership.user, Notification.Kind.STAGE_UP,
            award_id=award.id, number=award.number, name=membership.user.first_name or membership.user.display_name,
            stage=stage["name"], day=stage["day"], rank=stage["rank"] or stage["name"], award=stage["award"],
            description=stage["description"],
        )
    return award


def award_json(a):
    return {
        "id": a.id, "stage": a.stage.name, "day": a.stage.day, "award_type": a.stage.award_type,
        "award": a.stage.get_award_type_display(), "rank": a.stage.rank, "icon": a.stage.icon,
        "number": a.number, "issued_at": a.issued_at,
    }


# --- Fors-major ---------------------------------------------------------------

def freezes_left(membership, c=None):
    c = c or rules.current()
    return max(c.freezes_per_cohort - membership.freezes.count(), 0)


def request_freeze(membership, reason="", now=None):
    """Kasallik: oqimda sozlamadagi soncha, faqat kechqurun ertangi kun uchun."""
    now = local_now(now)
    c = rules.current()
    if freezes_left(membership, c) <= 0:
        raise RuleError("Muzlatish imkoniyatidan to'liq foydalangansiz.")
    if now.time() < c.freeze_allowed_from:
        raise RuleError(f"Muzlatishni faqat kechqurun ({c.freeze_allowed_from:%H:%M} dan keyin) oldindan bosish mumkin.")
    tomorrow = now.date() + dt.timedelta(days=1)
    if membership.cohort.day_number(tomorrow) is None:
        raise RuleError("Ertangi kun oqimga kirmaydi.")
    if membership.freezes.filter(date=tomorrow).exists():
        raise RuleError("Ertangi kun allaqachon muzlatilgan.")
    return Freeze.objects.create(membership=membership, date=tomorrow, reason=reason[:200])


def immunities_available(user):
    return Immunity.objects.filter(user=user, used_on__isnull=True).count()


# --- Startgacha: kutayotganlar, eslatma, mashq -------------------------------------

def upcoming_membership(user):
    """Qabul qilingan, lekin oqimi hali boshlanmagan ishtirok."""
    return (
        Membership.objects.select_related("cohort", "tribe", "squad", "user")
        .filter(user=user, status=Membership.Status.ACTIVE, cohort__status=Cohort.Status.RECRUITING)
        .order_by("cohort__start_date").first()
    )


def countdown_list(today=None):
    """Har kech yuboriladigan "Startga N kun qoldi" eslatmalari uchun."""
    today = today or local_now().date()
    result = []
    for m in Membership.objects.filter(
        status=Membership.Status.ACTIVE, cohort__status=Cohort.Status.RECRUITING, cohort__start_date__gt=today,
    ).select_related("cohort", "tribe", "squad", "user"):
        result.append({"telegram_id": m.user.telegram_id, **placement_payload(m), "days_left": days_until(m.cohort.start_date, today)})
    return result


@transaction.atomic
def clone_cohort(cohort, days=7):
    """Keyingi qabul: shu oqimning oynalari va tayyor rota vaqtlari bilan, start +N kun."""
    start = cohort.start_date + dt.timedelta(days=days)
    new = Cohort.objects.create(
        name=f"{start:%d.%m.%Y} oqimi", start_date=start, duration_days=cohort.duration_days,
        morning_window_start=cohort.morning_window_start, morning_window_end=cohort.morning_window_end,
        evening_window_start=cohort.evening_window_start, evening_window_end=cohort.evening_window_end,
    )
    WakeSlot.objects.bulk_create([
        WakeSlot(cohort=new, start_wake_time=s.start_wake_time, target_wake_time=s.target_wake_time, title=s.title)
        for s in cohort.slots.all()
    ])
    return new


# --- Rota raporti ---------------------------------------------------------------

def member_report(membership, date):
    """Bitta jangchining bugungi holati: done / woke / absent / frozen / rest / out."""
    if membership.status == Membership.Status.EXPELLED:
        return "out"
    record = membership.days.filter(date=date).select_related("video").first()
    if record is None:
        return "absent"
    if record.status in (DayRecord.Status.FROZEN, DayRecord.Status.REST, DayRecord.Status.COMPLETED, DayRecord.Status.FAILED):
        return {"completed": "done", "failed": "absent"}.get(record.status, record.status)
    progress = day_progress(record)
    if progress["proof_done"]:
        return "done"
    return "woke" if record.woke_at else "absent"


def squad_report(squad, date):
    members = squad.memberships.select_related("user").order_by("user__first_name")
    rows = [
        {
            "membership_id": m.id,
            "name": m.user.first_name or str(m.user),
            "telegram_id": m.user.telegram_id,
            "status": member_report(m, date),
            "strikes": m.active_strikes,
        }
        for m in members
    ]
    active = [r for r in rows if r["status"] != "out"]
    return {
        "squad": squad.name,
        "tribe": str(squad.tribe),
        "chat_id": squad.telegram_chat_id,
        "day_number": squad.tribe.cohort.day_number(date),
        "members": rows,
        "done": sum(r["status"] == "done" for r in active),
        "total": len(active),
    }
