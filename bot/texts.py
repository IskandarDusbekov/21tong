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

_config = {"settings": {}, "messages": {}, "loaded_at": 0.0}
REFRESH_SECONDS = 30


def escape(text):
    """HTML parse_mode uchun: faqat < > & — o'zbekcha apostroflar (o', g') tegilmaydi."""
    return html.escape(str(text), quote=False)


async def refresh(force=False):
    if not force and time.monotonic() - _config["loaded_at"] < REFRESH_SECONDS:
        return
    try:
        data = await backend.config()
        _config.update(settings=data["settings"], messages=data["messages"], loaded_at=time.monotonic())
    except Exception as e:  # backend vaqtincha ishlamasa — oxirgi matnlar bilan davom etamiz
        log.warning("Bot xabarlarini yangilab bo'lmadi: %s", e)


def setting(name, default=None):
    return _config["settings"].get(name, default)


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


def application_summary(d):
    return t("application_summary", gender=GENDER[d["gender"]], goal=escape(d["goal"]),
             current=d["current"], target=d["target"])


def approved(p):
    if not p.get("squad"):
        return t("approved_waiting")
    invite = t("invite_link", link=p["invite_link"]) if p.get("invite_link") else t("invite_pending")
    return t("approved", cohort=escape(p["cohort"]), start_date=p["start_date"], tribe=escape(p["tribe"]),
             squad=p["squad"], invite=invite)


def welcome_back(user):
    m = user.get("membership")
    if not m:
        return t("approved_waiting")
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


def squad_post(p):
    return t("squad_post", icon="🎥" if p["proof_kind"] == "video" else "🎙", name=escape(p["name"]), day=p["day_number"])


def review_request(p):
    return t("review_request", name=escape(p.get("name") or "Rotadosh"), day=p.get("day_number", ""),
             phrase=escape(p.get("phrase") or ""))


# --- Jazo va mukofot -------------------------------------------------------------------


def reason(code):
    return t(f"reason_{code}")


def strike(p):
    key = "strike_last" if p["count"] == p["max"] - 1 else "strike"
    return t(key, count=p["count"], reason=reason(p["reason"]))


def strike_public(p):
    return t("strike_public", name=escape(p["name"]), count=p["count"], reason=reason(p["reason"]))


def immunity_granted(source):
    return t(f"immunity_{source}") if source in ("referral", "sunday", "admin") else t("immunity_admin")


def stage_up(p):
    return t("stage_up", name=escape(p["name"]), day=p["day"], description=escape(p.get("description") or ""))


# --- Rota guruhi --------------------------------------------------------------------

ROLL_ICONS = {"done": "✅", "woke": "⏳", "absent": "❌", "frozen": "❄️", "rest": "😴", "out": "🚫"}
ROLL_NOTES = {"woke": " — turdi, raport yo'q", "absent": " — javob yo'q", "frozen": " — muzlatilgan", "rest": " — yakshanba"}


def roll_call(r):
    lines = [t("roll_call_header", squad=r["squad"], day=r["day_number"]), ""]
    for m in r["members"]:
        if m["status"] == "out":
            continue
        warn = f" · ⚠️{m['strikes']}" if m["strikes"] else ""
        lines.append(f"{ROLL_ICONS[m['status']]} {escape(m['name'])}{ROLL_NOTES.get(m['status'], '')}{warn}")
    lines += ["", t("roll_call_footer", done=r["done"], total=r["total"])]
    if r["total"] and r["done"] == r["total"]:
        lines.append(t("roll_call_all_done"))
    return "\n".join(lines)


# --- Qo'mondonlik (faqat adminlar ko'radi — kodda qoladi) ----------------------------


def new_application(p, telegram_id):
    who = escape(p.get("name") or "—") + (f" (@{escape(p['username'])})" if p.get("username") else "")
    ref = f"\nTaklif qilgan: {escape(p['referred_by'])}" if p.get("referred_by") else ""
    return (
        "📥 <b>YANGI ARIZA</b>\n\n"
        f"Kim: {who}\nID: <code>{telegram_id}</code>\n"
        f"Jins: {GENDER.get(p.get('gender'), '—')}\n"
        f"Turadi: {p.get('current_wake_time') or '—'} → maqsad {p.get('target_wake_time') or '—'}\n"
        f"Maqsad: <i>{escape(p.get('goal') or '')}</i>{ref}"
    )


def squad_linked(r):
    return f"✅ Guruh <b>{r['name']}</b> ga ulandi ({escape(r['tribe'])}). Endi raportlar shu yerga keladi."


NOT_ADMIN = "Bu buyruq faqat adminlar uchun."
NO_PENDING = "Yangi ariza yo'q."
LINK_HELP = "Bu buyruqni rota guruhining ichida yozing. Bot guruhda admin bo'lishi kerak."
NO_SQUADS = "Ulanmagan rota yo'q. Avval arizalarni tasdiqlang — rotalar o'zi ochiladi."
