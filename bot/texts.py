"""
Bot xarakteri: Adolatli Serjant (ertalab / jazoda) + Mehribon Murabbiy (yutuq / qo'llab-quvvatlash).
Barcha matnlar shu yerda — ohangni bir joydan boshqarish uchun.
"""
import random

WELCOME = (
    "Assalomu alaykum! Bu — <b>21 Tong</b>.\n\n"
    "21 kun. Qat'iy intizom. Yangi uyqu rejimi.\n"
    "Bu yerda bahona yo'q — faqat harakat bor.\n\n"
    "Boshlaymiz. Avval ayting: siz kimsiz?"
)
ASK_GOAL = (
    "Endi maqsadingizni yozing. Nima uchun keldingiz?\n"
    "<i>Masalan: \"Har kuni 5:30 da turib, bomdod va sportni qoldirmayman.\"</i>"
)
GOAL_TOO_SHORT = "Bu maqsad emas, bu bahona. Kamida 10 belgi — aniqroq yozing."
PENDING = (
    "Anketangiz qabul qilindi. Admin ko'rib chiqadi va tasdiqlasa, yopiq guruhga yo'llanma olasiz.\n\n"
    "Mana sizning <b>Manifestingiz</b> 👇"
)
MANIFEST_CAPTION = (
    "Buni storisga joylang va do'stlaringizni taklif qiling.\n"
    "Sizning havolangiz orqali kelgan do'stingiz tasdiqlansa — loyiha boshlanmasidanoq "
    "<b>1 ta Joker 🃏</b> yutib olasiz.\n\n"
    "Havola: {link}"
)
ALREADY_PENDING = "Anketangiz hali ko'rib chiqilmoqda. Sabr — bu ham intizom."
REJECTED = "Afsus, bu safar anketangiz tasdiqlanmadi. Keyingi oqimda yana urinib ko'ring."
APPROVED = (
    "Tabriklayman! Siz qabul qilindingiz. 🎯\n"
    "Endi oqimni va uyg'onish vaqtingizni tanlaymiz: /join"
)
NOT_REGISTERED = "Avval ro'yxatdan o'ting: /start"

ASK_START_TIME = "Hozir odatda soat nechada turasiz? (Masalan: <code>07:00</code>)"
ASK_TARGET_TIME = (
    "Maqsadingiz qaysi vaqt? (Masalan: <code>05:30</code>)\n"
    "7-kundan boshlab budilnik har kuni 5 daqiqaga oldinga suriladi — maqsadga silliq yetasiz."
)
BAD_TIME = "Vaqtni HH:MM formatida yozing, masalan 06:30."
NO_COHORTS = "Hozircha qabul ochiq oqim yo'q. E'lon qilinishi bilan xabar beramiz."
JOINED = "Siz <b>{tribe}</b> safidasiz. Guruhga kiring: {link}\nBirinchi tongda ko'rishguncha!"

ALARM = [
    "⏰ Turing! Bugun {day}-kun. Sen o'zgaraman deb kelganding. Qani harakat!",
    "⏰ {day}-kun. Ko'rpa seni ushlab turibdi — sen esa undan kuchliroqsan. Tur!",
    "⏰ Uyg'on! {day}-kun. Bahona emas, natija kerak.",
]
STEPS = (
    "1️⃣ Mini App'da «Uyg'ondim» tugmasini bosing\n"
    "2️⃣ Quyidagi gapni ovoz chiqarib o'qib, guruhga voice yuboring\n"
    "3️⃣ Tashqariga chiqib, suv iching va 10 soniyalik video krujokni shu yerga yuboring"
)
COGNITIVE = [
    "Men bugun o'z irodamning xo'jayiniman.",
    "Intizom — bu o'zimga bergan va'damni bajarish.",
    "Har bir erta tong — kelajagimga qo'yilgan sarmoya.",
    "Qiyinchilik vaqtinchalik, odat esa abadiy.",
]
FACELESS_HINT = "\n\n<i>Qizlar uchun: yuzingizni ko'rsatish shart emas — ko'cha/oyna tomonga suratga oling, ovozingiz eshitilsin.</i>"

VOICE_OK = "🎙 Qabul qilindi. Endi tashqariga — suv va video krujok."
VIDEO_SENT = "📹 Video 3 ta ishtirokchiga tekshirish uchun yuborildi. Natijani kuting."
VIDEO_AUTO = "📹 Video qabul qilindi."
REVIEW_REQUEST = "Tekshiruv: bu ishtirokchi bugun vazifani bajardimi? Halol baho bering."
VOTE_THANKS = "Rahmat, ovozingiz hisobga olindi."
VIDEO_APPROVED = "✅ Jamoa videongizni tasdiqladi. {day}-kun yopildi. Zo'r!"
VIDEO_REJECTED = "❌ Jamoa videongizni tasdiqlamadi. Ertaga buni takrorlamang."

STRIKE = (
    "❌ <b>Strike {count}/{max}</b> — {reason}.\n"
    "Sen o'zgaraman deb kelganding. Yana bitta xato qilsang, sendan umidni uzamiz."
)
STRIKE_REASONS = {
    "late": "vaqtida turmading",
    "no_voice": "ovozli xabar yubormading",
    "no_video": "video yubormading",
    "rejected": "jamoa tasdiqlamadi",
    "admin": "admin qarori",
}
JOKER_USED = "🃏 Joker seni qutqardi ({reason}). Bu oxirgi imkoniyat bo'lishi mumkin — ehtiyot bo'l."
JOKER_GRANTED = {
    "referral": "🃏 Do'stingiz qo'shildi — sizga 1 ta Joker! U kelajakdagi 1 ta Strike'ni o'chiradi.",
    "sunday": "🃏 Yakshanba ham barvaqt turding! Sovg'a — 1 ta Joker. Men senga ishonaman!",
}
EXPELLED = (
    "3 ta Strike. Qoida hamma uchun bir xil — siz loyihadan chiqarildingiz.\n"
    "Bu oxiri emas. Keyingi oqimda qaytib, isbotlab ko'rsating."
)
STAGE_UP = (
    "🏅 <b>{name}</b>! Siz {day} kunni ortda qoldirdingiz.\n"
    "Hozir qanchalik qiyin bo'lmasin, sen zo'r ketyapsan. Men senga ishonaman!"
)
CHAT_OPEN = {"morning": "🌅 Tonggi oyna ochildi. Bir-biringizni uyg'oting!", "evening": "🌙 Kechki oyna ochildi. Bugungi kun qanday o'tdi? (Mini App → Refleksiya)"}
CHAT_CLOSED = "🔒 Oyna yopildi. Keyingi oynada ko'rishamiz."


def alarm(day):
    return random.choice(ALARM).format(day=day)


def cognitive_phrase():
    return random.choice(COGNITIVE)
