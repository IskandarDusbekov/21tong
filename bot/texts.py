"""
Bot xarakteri: Adolatli Serjant (buyruq, raport, jazo) + Mehribon Murabbiy (yutuq, qo'llab-quvvatlash).
Lager ohangi: qisqa, aniq, buyruq shaklida. Barcha matnlar shu yerda.
"""
import html
import random


def escape(text):
    """HTML parse_mode uchun: faqat < > & — o'zbekcha apostroflar (o', g') tegilmaydi."""
    return html.escape(str(text), quote=False)


GENDER = {"M": "Yigit", "F": "Qiz"}

# --- Ariza ---------------------------------------------------------------------

WELCOME = (
    "🎖 <b>21 TONG — intizom lageri</b>\n\n"
    "21 kun. Har tong — raport. Bahona qabul qilinmaydi.\n\n"
    "<b>Nizom qisqacha:</b>\n"
    "• Har kuni budilnik bo'yicha turasan va «Uyg'ondim» bosasan\n"
    "• Bot bergan gapni ovoz chiqarib o'qib raport yuborasan\n"
    "• 7-kundan — tashqariga chiqib video krujok\n"
    "• 7 kishilik rotada yashaysan, rotadoshlaring tekshiradi\n"
    "• 3 ta ogohlantirish — lagerdan chiqarilasan\n\n"
    "Tayyormisan? Arizani to'ldiramiz.\n\n"
    "<b>1/4.</b> Jinsingiz:"
)
ASK_GOAL = (
    "<b>2/4.</b> Nima uchun keldingiz? Maqsadingizni yozing.\n"
    "<i>Masalan: «Har kuni 5:30 da turib, bomdod va sportni qoldirmayman.»</i>"
)
GOAL_TOO_SHORT = "Bu maqsad emas, bu bahona. Kamida 10 belgi — aniqroq yozing."
ASK_CURRENT_TIME = "<b>3/4.</b> Hozir odatda soat nechada turasiz? (Masalan: <code>07:00</code>)"
ASK_TARGET_TIME = (
    "<b>4/4.</b> Qaysi vaqtda turishni maqsad qilasiz? (Masalan: <code>05:30</code>)\n"
    "<i>7-kundan budilnik har kuni 5 daqiqa oldinga suriladi — maqsadga silliq yetasiz.</i>"
)
BAD_TIME = "Vaqtni HH:MM formatida yozing, masalan 06:30."
TARGET_LATER = "Maqsad vaqti hozirgidan erta bo'lishi kerak. Qaytadan yozing."


def application_summary(d):
    return (
        "📝 <b>Arizangiz</b>\n\n"
        f"Jins: {GENDER[d['gender']]}\n"
        f"Maqsad: {escape(d['goal'])}\n"
        f"Hozir turadi: <b>{d['current']}</b>\n"
        f"Maqsad vaqti: <b>{d['target']}</b>\n\n"
        "Hammasi to'g'rimi? Yuborilgandan keyin jinsni o'zgartirib bo'lmaydi."
    )


SUBMITTED = (
    "✅ Ariza qabul qilindi va qo'mondonlikka yuborildi.\n"
    "Tasdiqlangach, sizni rotaga joylashtiramiz va guruh havolasini yuboramiz.\n\n"
    "Mana sizning <b>Manifestingiz</b> 👇"
)
MANIFEST_CAPTION = (
    "Storisga joylang va do'stlaringizni chaqiring.\n"
    "Havolangiz orqali kelgan do'stingiz qabul qilinsa — loyiha boshlanmasidanoq <b>1 ta Joker 🃏</b>.\n\n"
    "Havola: {link}"
)
ALREADY_PENDING = "⏳ Arizangiz ko'rib chiqilmoqda. Sabr — bu ham intizom."
REJECTED = "Afsus, bu safar arizangiz qabul qilinmadi. Keyingi oqimda yana urinib ko'ring."
NOT_REGISTERED = "Avval ariza qoldiring: /start"


def approved(p):
    if p.get("squad"):
        link = p.get("invite_link")
        return (
            "🎖 <b>QABUL QILINDINGIZ!</b>\n\n"
            f"Oqim: <b>{escape(p['cohort'])}</b> · start {p['start_date']}\n"
            f"Qabila: {escape(p['tribe'])}\n"
            f"Rota: <b>{p['squad']}</b> (7 kishi)\n\n"
            + (f"Rota guruhiga kiring: {link}" if link else "Rota guruhi havolasi tez orada keladi.")
            + "\n\nBirinchi tongda saf tortamiz. Kech qolma."
        )
    return "🎖 <b>QABUL QILINDINGIZ!</b>\nYangi oqim e'lon qilinganda rotaga joylashtirasiz. Kuzatib boring."


def welcome_back(user):
    m = user.get("membership")
    if not m:
        return "Siz qabul qilingansiz. Oqim e'lon qilinishini kuting yoki /join."
    return (
        f"🎖 {escape(user.get('name') or 'Jangchi')}, saf tortish joyingiz:\n"
        f"{escape(m['tribe'])} · <b>{m['squad'] or '—'}</b>\n"
        f"Ogohlantirishlar: {m['strikes']}/3 · Joker: {user['jokers']}\n\n"
        "Buyruqlar: /holat — bugungi holat, /nizom — lager qoidalari"
    )


RULES = (
    "📜 <b>LAGER NIZOMI</b>\n\n"
    "<b>1. Turish.</b> Budilnikdan keyin 5 daqiqa ichida «Uyg'ondim».\n"
    "<b>2. Raport.</b> Bot bergan gapni ovoz chiqarib o'qing va 30 daqiqa ichida shu botga yuboring:\n"
    "   • 1–6 kun — ovozli xabar\n"
    "   • 7-kundan — tashqarida, kamera ko'chaga qaragan video krujok\n"
    "<b>3. Tekshiruv.</b> Videoni rotadan 3 kishi ko'radi, 2 tasi tasdiqlasa — qabul.\n"
    "<b>4. Oynalar.</b> Rota chati 05:30–07:30 va 20:30–21:30 da ochiq.\n"
    "<b>5. Jazo.</b> Bajarmaslik = ogohlantirish. 3 ta — lagerdan chiqarilasiz.\n"
    "<b>6. Yakshanba.</b> Uxlash mumkin. Barvaqt turib bajarsangiz — Joker 🃏.\n"
    "<b>7. Joker.</b> Keyingi ogohlantirishni o'chiradi.\n"
    "<b>8. Kasallik.</b> Oqimda 1 marta, kechqurun oldindan — ertangi kun muzlatiladi.\n\n"
    "Bosqichlar: 3-kun Omon qolgan → 7-kun Moslashgan → 21-kun Temir Iroda → 40-kun Mentor."
)

# --- Admin ---------------------------------------------------------------------


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


NOT_ADMIN = "Bu buyruq faqat adminlar uchun."
NO_PENDING = "Yangi ariza yo'q."
LINK_HELP = "Bu buyruqni rota guruhining ichida yozing. Bot guruhda admin bo'lishi kerak."
NO_SQUADS = "Ulanmagan rota yo'q. Avval arizalarni tasdiqlang — rotalar o'zi ochiladi."

# --- Tonggi zanjir -----------------------------------------------------------------

ALARM = [
    "⏰ <b>TURISH!</b> {day}-kun · {time}\nRota, oyoqqa! Sen o'zgaraman deb kelganding.",
    "⏰ <b>TURISH!</b> {day}-kun · {time}\nKo'rpa seni ushlab turibdi — sen esa undan kuchliroqsan.",
    "⏰ <b>TURISH!</b> {day}-kun · {time}\nBahona emas, natija kerak. Rotang seni kutyapti.",
]
ALARM_HINT = "Pastdagi tugmani bosing — bugungi buyruq va o'qiladigan gap beriladi."


def alarm(day, time):
    return random.choice(ALARM).format(day=day, time=time)


def order(p, gender):
    head = f"📣 <b>BUYRUQ №{p['day_number']}</b>\n\nOvoz chiqarib o'qing:\n<blockquote>{escape(p['phrase'])}</blockquote>\n"
    if p["proof_kind"] == "video":
        body = (
            "📍 Tashqariga (ko'cha yoki hovliga) chiqing, suv iching.\n"
            "🎥 <b>Video krujok</b> yozing (10–20 soniya): kamera atrofga qaragan, yurib turib gapni o'qing.\n"
        )
        if gender == "F":
            body += "<i>Yuzingizni ko'rsatish shart emas — orqa kamerani yoqing, ovozingiz eshitilsin.</i>\n"
    else:
        body = "🎙 <b>Ovozli xabar</b> yozib, shu yerga yuboring.\n"
    return head + body + f"\n⏱ Muddat: <b>{p['proof_deadline']}</b> gacha."


VOICE_OK = "✅ Raport qabul qilindi. {day}-kun bajarildi. Rotangizga e'lon qilindi."
VIDEO_SENT = "✅ Video qabul qilindi. Rotadoshlaringizdan 3 kishi tekshiradi — natija keladi."
VIDEO_AUTO = "✅ Video qabul qilindi."


def squad_post(p):
    icon = "🎥" if p["proof_kind"] == "video" else "🎙"
    return f"{icon} <b>{escape(p['name'])}</b> — {p['day_number']}-kun raporti"


def review_request(p):
    return (
        f"🔍 <b>TEKSHIRUV</b> · {escape(p.get('name') or 'Rotadosh')}, {p.get('day_number', '')}-kun\n\n"
        f"O'qilishi kerak bo'lgan gap:\n<blockquote>{escape(p.get('phrase') or '')}</blockquote>\n"
        "Shartlar: tashqarida yozilgan, gap aniq o'qilgan.\nHalol baho bering."
    )


VOTE_THANKS = "Ovozingiz hisobga olindi."
VIDEO_APPROVED = "✅ Rota videongizni tasdiqladi. {day}-kun yopildi. Zo'r!"
VIDEO_REJECTED = "❌ Rota videongizni tasdiqlamadi. Bu kun bajarilmagan hisoblanadi."
UNKNOWN_MEDIA = "Raport uchun ovozli xabar (1–6 kun) yoki video krujok (7-kundan) yuboring."

# --- Jazo va mukofot ---------------------------------------------------------------

STRIKE_REASONS = {
    "late": "vaqtida turmadi",
    "no_voice": "ovozli raport yo'q",
    "no_video": "video raport yo'q",
    "rejected": "rota tasdiqlamadi",
    "admin": "qo'mondonlik qarori",
}


def strike(p):
    reason = STRIKE_REASONS.get(p["reason"], p["reason"])
    tail = (
        "Yana bitta xato — lagerdan chiqasan. Ertaga isbotla."
        if p["count"] == p["max"] - 1
        else "Sen o'zgaraman deb kelganding. Qani harakat!"
    )
    return f"⚠️ <b>OGOHLANTIRISH {p['count']}/{p['max']}</b> — {reason}.\n{tail}"


def strike_public(p):
    reason = STRIKE_REASONS.get(p["reason"], p["reason"])
    return f"⚠️ <b>{escape(p['name'])}</b> — ogohlantirish {p['count']}/{p['max']} ({reason})."


JOKER_USED = "🃏 Joker seni qutqardi ({reason}). Ogohlantirish o'chirildi — endi ehtiyot bo'l."
JOKER_GRANTED = {
    "referral": "🃏 Do'stingiz qabul qilindi — sizga 1 ta Joker! U keyingi ogohlantirishni o'chiradi.",
    "sunday": "🃏 Yakshanba ham barvaqt turding! Sovg'a — 1 ta Joker. Men senga ishonaman!",
}
EXPELLED = (
    "🚫 3 ta ogohlantirish. Nizom hamma uchun bir xil — siz lagerdan chiqarildingiz.\n"
    "Bu oxiri emas. Keyingi oqimda qaytib, isbotlab ko'rsating."
)


def expelled_public(p):
    return f"🚫 <b>{escape(p['name'])}</b> 3 ta ogohlantirish oldi va lagerdan chiqarildi."


def stage_up(p):
    return (
        f"🏅 <b>{p['name']}</b>! Siz {p['day']} kunni ortda qoldirdingiz.\n"
        "Hozir qanchalik qiyin bo'lmasin, sen zo'r ketyapsan. Men senga ishonaman!"
    )


# --- Rota guruhi ------------------------------------------------------------------

CHAT_OPEN = {
    "morning": "🌅 <b>Tonggi oyna ochildi.</b> Saf torting! Uxlab qolganlarni uyg'oting.",
    "evening": "🌙 <b>Kechki oyna ochildi.</b> Bugungi kun qanday o'tdi? Refleksiya — Mini App'da.",
}
CHAT_CLOSED = "🔒 Oyna yopildi. Keyingi oynada ko'rishamiz."

ROLL_ICONS = {"done": "✅", "woke": "⏳", "absent": "❌", "frozen": "❄️", "rest": "😴", "out": "🚫"}
ROLL_NOTES = {"woke": " — turdi, raport yo'q", "absent": " — javob yo'q", "frozen": " — muzlatilgan", "rest": " — yakshanba"}


def roll_call(r):
    lines = [f"📋 <b>TONGGI RAPORT</b> · {r['squad']} · {r['day_number']}-kun\n"]
    for m in r["members"]:
        if m["status"] == "out":
            continue
        warn = f" · ⚠️{m['strikes']}" if m["strikes"] else ""
        lines.append(f"{ROLL_ICONS[m['status']]} {escape(m['name'])}{ROLL_NOTES.get(m['status'], '')}{warn}")
    lines.append(f"\nSafda: <b>{r['done']}/{r['total']}</b>")
    if r["total"] and r["done"] == r["total"]:
        lines.append("Butun rota saf tortdi. Mana bu — intizom! 💪")
    return "\n".join(lines)


def squad_linked(r):
    return f"✅ Guruh <b>{r['name']}</b> ga ulandi ({escape(r['tribe'])}). Endi raportlar shu yerga keladi."


def squad_invite(name, link):
    return f"🎖 Rotangiz guruhi tayyor: <b>{name}</b>\nKirish: {link}"


JOIN_DENIED = "Bu guruh faqat shu rota a'zolari uchun."
