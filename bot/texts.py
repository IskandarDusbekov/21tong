"""
Bot matnlari. Foydalanuvchiga boradigan barcha xabarlar admin paneldagi "Bot xabarlari"dan olinadi
(backend /api/bot/config/) va har 30 soniyada yangilanadi — matnni o'zgartirish uchun kod yozish shart emas.
Bu yerda faqat ularni yig'uvchi funksiyalar va adminlarga ko'rinadigan xizmat matnlari.
"""
import html
import logging
import random
import time

from api import backend

log = logging.getLogger(__name__)

_config = {"settings": {}, "messages": {}, "regions": [], "loaded_at": 0.0}
REFRESH_SECONDS = 30


def escape(text):
    """HTML parse_mode uchun: faqat < > & — o'zbekcha apostroflar (o', g') tegilmaydi."""
    return html.escape(str(text), quote=False)


async def refresh(force=False):
    if not force and time.monotonic() - _config["loaded_at"] < REFRESH_SECONDS:
        return
    try:
        data = await backend.config()
        _config.update(settings=data["settings"], messages=data["messages"], regions=data.get("regions", []),
                       loaded_at=time.monotonic())
    except Exception as e:  # backend vaqtincha ishlamasa — oxirgi matnlar bilan davom etamiz
        log.warning("Bot xabarlarini yangilab bo'lmadi: %s", e)


def setting(name, default=None):
    return _config["settings"].get(name, default)


def regions():
    return _config["regions"]


class _Vars(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def t(key, **values):
    """Admin paneldagi matnni o'zgaruvchilar bilan to'ldiradi. Bir nechta variant bo'lsa (---) — tasodifiy."""
    template = _config["messages"].get(key, key)
    variants = [v.strip() for v in template.split("\n---\n")]
    try:
        return random.choice(variants).format_map(_Vars({**_config["settings"], **values}))
    except (ValueError, IndexError) as e:
        log.warning("%s xabarida xato: %s", key, e)
        return random.choice(variants)


GENDER = {"M": "Yigit", "F": "Qiz"}

# --- Ariza ------------------------------------------------------------------------


def slot_label(s):
    label = f"{s['start_wake_time']} → {s['target_wake_time']}"
    return label + (f" · {s['title']}" if s.get("title") else "")


def application_summary(d):
    slot = d["slot"]
    return t(
        "application_summary", full_name=escape(f"{d['first_name']} {d['last_name']}"),
        region=escape(d["region_label"]), gender=GENDER[d["gender"]], goal=escape(d["goal"]),
        slot=escape(slot_label(slot)), start_date=slot["cohort"]["start_label"],
    )


def ask_slot(slots):
    c = slots[0]["cohort"]
    return t("ask_slot", cohort=escape(c["name"]), start_date=c["start_label"], days_left=c["days_left"])


def approved(p):
    if not p.get("squad"):
        return t("approved_waiting")
    return t("approved", name=escape(p.get("name", "")), cohort=escape(p["cohort"]), start_date=p["start_date"],
             days_left=p.get("days_left", ""), tribe=escape(p["tribe"]), squad=p["squad"],
             alarm=p.get("alarm", ""), target=p.get("target", ""))


def practice(p):
    up = p.get("upcoming")
    if not up:
        return t("practice_waiting")
    return t("practice_ok", start_date=up["start_date"], days_left=up["days_left"], alarm=up["alarm"])


def countdown(r):
    if r["days_left"] <= 1:
        return t("countdown_tomorrow", alarm=r["alarm"], squad=r["squad"])
    return t("countdown", days_left=r["days_left"], start_date=r["start_date"], squad=r["squad"], alarm=r["alarm"])


def welcome_back(user):
    m = user.get("membership")
    if not m:
        return t("approved_waiting")
    if user.get("upcoming"):
        return countdown(user["upcoming"])
    return t("welcome_back", name=escape(user.get("name") or "Jangchi"), tribe=escape(m["tribe"]),
             squad=m["squad"] or "—", strikes=m["strikes"], immunities=user["immunities"])


# --- Tonggi zanjir -------------------------------------------------------------------


def alarm(day, time_):
    return f"{t('alarm', day=day, time=time_)}\n\n{t('alarm_hint')}"


def order(p, gender):
    values = dict(day=p["day_number"], phrase=escape(p["phrase"]), deadline=p["proof_deadline"],
                  minutes=p.get("proof_minutes", ""))
    if p["proof_kind"] == "video":
        text = t("order_video", **values)
        return f"{text}\n\n{t('order_female_hint')}" if gender == "F" else text
    return t("order_voice", **values)


def review_request(p):
    return t("review_request", name=escape(p.get("name") or "Rotadosh"), day=p.get("day_number", ""),
             phrase=escape(p.get("phrase") or ""))


# --- Jazo va mukofot -------------------------------------------------------------------


def reason(code):
    return t(f"reason_{code}")


def strike(p):
    key = "strike_last" if p["count"] == p["max"] - 1 else "strike"
    return t(key, count=p["count"], reason=reason(p["reason"]))


def immunity_granted(source):
    return t(f"immunity_{source}") if source in ("referral", "sunday", "admin") else t("immunity_admin")


def award_caption(p):
    return t("award_caption", name=escape(p["name"]), stage=escape(p["stage"]), day=p["day"], rank=escape(p["rank"]),
             award=escape(p["award"]), description=escape(p.get("description") or ""), number=p["number"])


# --- Qo'mondonlik (faqat adminlar ko'radi — kodda qoladi) ----------------------------


def new_application(p, telegram_id):
    who = escape(p.get("name") or "—") + (f" (@{escape(p['username'])})" if p.get("username") else "")
    ref = f"\nTaklif qilgan: {escape(p['referred_by'])}" if p.get("referred_by") else ""
    return (
        "📥 <b>YANGI ARIZA</b>\n\n"
        f"Kim: {who}\nID: <code>{telegram_id}</code>\n"
        f"Jins: {GENDER.get(p.get('gender'), '—')} · {escape(p.get('region') or '—')}\n"
        f"Rota: {escape(p.get('slot') or '—')}\n"
        f"Maqsad: <i>{escape(p.get('goal') or '')}</i>{ref}"
    )


NOT_ADMIN = "Bu buyruq faqat adminlar uchun."
NO_PENDING = "Yangi ariza yo'q."
