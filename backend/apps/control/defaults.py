"""
Bot xabarlarining standart matnlari. Admin panelda har birini tahrirlash mumkin;
"Standartga qaytarish" amali shu yerdagi matnni tiklaydi.

Matnlarda {o'zgaruvchi} ko'rinishidagi joylar bot tomonidan to'ldiriladi. Har bir xabarda
o'zining o'zgaruvchilari, hamma xabarlarda esa lager sozlamalari mavjud:
  {wake_grace} {voice_deadline} {video_deadline} {shift_from_day} {shift_step} {video_from_day}
  {max_strikes} {squad_size} {reviewers} {freeze_from} {duration}
HTML teglar: <b>qalin</b>, <i>kursiv</i>, <blockquote>iqtibos</blockquote>, <code>kod</code>.
"""

SETTINGS_VARS = (
    "wake_grace", "voice_deadline", "video_deadline", "shift_from_day", "shift_step",
    "video_from_day", "max_strikes", "squad_size", "reviewers", "freeze_from", "duration",
)

# kalit: (guruh, sarlavha, xabarning o'z o'zgaruvchilari, matn)
MESSAGES = {
    # --- Ariza ---
    "welcome": ("Ariza", "Kirish (/start)", (), (
        "🎖 <b>21 TONG — intizom lageri</b>\n\n"
        "{duration} kun. Har tong — raport. Bahona qabul qilinmaydi.\n\n"
        "<b>Nizom qisqacha:</b>\n"
        "• Budilnik bo'yicha turasan va {wake_grace} daqiqa ichida «Uyg'ondim» bosasan\n"
        "• {voice_deadline} daqiqa ichida bot bergan gapni o'qib, ovozli raport yuborasan\n"
        "• {shift_from_day}-kundan budilnik har kuni {shift_step} daqiqa oldinga suriladi\n"
        "• {squad_size} kishilik rotada yashaysan, rotadoshlaring seni ko'rib turadi\n"
        "• {max_strikes} ta ogohlantirish — lagerdan chiqarilasan\n\n"
        "Tayyormisan? Arizani to'ldiramiz.\n\n"
        "<b>1/4.</b> Jinsingiz:"
    )),
    "registration_closed": ("Ariza", "Qabul yopiq", (), (
        "Hozircha ariza qabul qilinmayapti. Keyingi oqim e'lon qilinishini kuting."
    )),
    "ask_goal": ("Ariza", "2-savol: maqsad", (), (
        "<b>2/4.</b> Nima uchun keldingiz? Maqsadingizni yozing.\n"
        "<i>Masalan: «Har kuni 5:30 da turib, bomdod va sportni qoldirmayman.»</i>"
    )),
    "goal_too_short": ("Ariza", "Maqsad juda qisqa", (), "Bu maqsad emas, bu bahona. Kamida 10 belgi — aniqroq yozing."),
    "ask_current_time": ("Ariza", "3-savol: hozirgi vaqt", (), (
        "<b>3/4.</b> Hozir odatda soat nechada turasiz? (Masalan: <code>07:00</code>)"
    )),
    "ask_target_time": ("Ariza", "4-savol: maqsad vaqti", (), (
        "<b>4/4.</b> Qaysi vaqtda turishni maqsad qilasiz? (Masalan: <code>05:30</code>)\n"
        "<i>{shift_from_day}-kundan budilnik har kuni {shift_step} daqiqa oldinga suriladi — maqsadga silliq yetasiz.</i>"
    )),
    "bad_time": ("Ariza", "Vaqt formati xato", (), "Vaqtni HH:MM formatida yozing, masalan 06:30."),
    "target_later": ("Ariza", "Maqsad vaqti kech", (), "Maqsad vaqti hozirgidan erta bo'lishi kerak. Qaytadan yozing."),
    "application_summary": ("Ariza", "Arizani tasdiqlash", ("gender", "goal", "current", "target"), (
        "📝 <b>Arizangiz</b>\n\n"
        "Jins: {gender}\nMaqsad: {goal}\nHozir turadi: <b>{current}</b>\nMaqsad vaqti: <b>{target}</b>\n\n"
        "Hammasi to'g'rimi? Yuborilgandan keyin jinsni o'zgartirib bo'lmaydi."
    )),
    "submitted": ("Ariza", "Ariza yuborildi", (), (
        "✅ Ariza qabul qilindi va qo'mondonlikka yuborildi.\n"
        "Tasdiqlangach, sizni rotaga joylashtiramiz va guruh havolasini yuboramiz.\n\n"
        "Mana sizning <b>Manifestingiz</b> 👇"
    )),
    "manifest_caption": ("Ariza", "Manifest rasmi ostidagi matn", ("link",), (
        "Storisga joylang va do'stlaringizni chaqiring.\n"
        "Havolangiz orqali kelgan do'stingiz qabul qilinsa — loyiha boshlanmasidanoq <b>1 ta Immunitet 🛡</b>.\n\n"
        "Havola: {link}"
    )),
    "already_pending": ("Ariza", "Ariza ko'rib chiqilmoqda", (), "⏳ Arizangiz ko'rib chiqilmoqda. Sabr — bu ham intizom."),
    "rejected": ("Ariza", "Ariza rad etildi", (), "Afsus, bu safar arizangiz qabul qilinmadi. Keyingi oqimda yana urinib ko'ring."),
    "not_registered": ("Ariza", "Ro'yxatdan o'tmagan", (), "Avval ariza qoldiring: /start"),
    "approved": ("Ariza", "Qabul qilindi (rotaga joylashdi)", ("cohort", "start_date", "tribe", "squad", "invite"), (
        "🎖 <b>QABUL QILINDINGIZ!</b>\n\n"
        "Oqim: <b>{cohort}</b> · start {start_date}\n"
        "Qabila: {tribe}\n"
        "Rota: <b>{squad}</b>\n\n"
        "{invite}\n\n"
        "Birinchi tongda saf tortamiz. Kech qolma."
    )),
    "approved_waiting": ("Ariza", "Qabul qilindi (oqim hali yo'q)", (), (
        "🎖 <b>QABUL QILINDINGIZ!</b>\nYangi oqim e'lon qilinganda rotaga joylashtirasiz. Kuzatib boring."
    )),
    "invite_link": ("Ariza", "Guruh havolasi qatori", ("link",), "Rota guruhiga kiring: {link}"),
    "invite_pending": ("Ariza", "Guruh havolasi hali yo'q", (), "Rota guruhi havolasi tez orada keladi."),
    "welcome_back": ("Ariza", "Holat (/holat)", ("name", "tribe", "squad", "strikes", "immunities"), (
        "🎖 {name}, saf tortish joyingiz:\n"
        "{tribe} · <b>{squad}</b>\n"
        "Ogohlantirishlar: {strikes}/{max_strikes} · Immunitet: {immunities}\n\n"
        "Buyruqlar: /holat — holat, /nizom — lager qoidalari"
    )),
    "rules": ("Ariza", "Lager nizomi (/nizom)", (), (
        "📜 <b>LAGER NIZOMI</b>\n\n"
        "<b>1. Turish.</b> Budilnikdan keyin {wake_grace} daqiqa ichida «Uyg'ondim» tugmasini bosing.\n"
        "<b>2. Raport.</b> Bot bergan gapni ovoz chiqarib o'qing va budilnikdan keyin {voice_deadline} daqiqa ichida "
        "shu botga <b>ovozli xabar</b> yuboring.\n"
        "<b>3. Kaizen.</b> {shift_from_day}-kundan budilnik har kuni {shift_step} daqiqa oldinga suriladi — maqsad vaqtigacha.\n"
        "<b>4. Rota.</b> {squad_size} kishilik rotada yashaysiz. Raportingiz rota guruhiga e'lon qilinadi.\n"
        "<b>5. Oynalar.</b> Rota chati faqat tong va kechqurun belgilangan vaqtda ochiq.\n"
        "<b>6. Jazo.</b> Bajarmaslik = ogohlantirish. {max_strikes} ta — lagerdan chiqarilasiz.\n"
        "<b>7. Yakshanba.</b> Uxlash mumkin. Barvaqt turib bajarsangiz — Immunitet 🛡.\n"
        "<b>8. Immunitet.</b> Keyingi ogohlantirishni o'chiradi.\n"
        "<b>9. Kasallik.</b> Oqimda bir marta, {freeze_from} dan keyin oldindan — ertangi kun muzlatiladi.\n\n"
        "Bosqichlar: 3-kun Omon qolgan → 7-kun Moslashgan → 21-kun Temir Iroda → 40-kun Mentor."
    )),

    # --- Tonggi zanjir ---
    "alarm": ("Tong", "Budilnik (variantlar --- bilan ajratiladi)", ("day", "time"), (
        "⏰ <b>TURISH!</b> {day}-kun · {time}\nRota, oyoqqa! Sen o'zgaraman deb kelganding.\n"
        "---\n"
        "⏰ <b>TURISH!</b> {day}-kun · {time}\nKo'rpa seni ushlab turibdi — sen esa undan kuchliroqsan.\n"
        "---\n"
        "⏰ <b>TURISH!</b> {day}-kun · {time}\nBahona emas, natija kerak. Rotang seni kutyapti."
    )),
    "alarm_hint": ("Tong", "Budilnik ostidagi izoh", (), (
        "{wake_grace} daqiqa ichida pastdagi tugmani bosing — bugungi buyruq va o'qiladigan gap beriladi."
    )),
    "order_voice": ("Tong", "Buyruq: ovozli raport", ("day", "phrase", "deadline", "minutes"), (
        "📣 <b>BUYRUQ №{day}</b>\n\n"
        "Ovoz chiqarib, aniq o'qing:\n<blockquote>{phrase}</blockquote>\n"
        "🎙 <b>Ovozli xabar</b> yozib, shu yerga yuboring.\n\n"
        "⏱ Muddat: <b>{deadline}</b> gacha. Kechiksang — ogohlantirish."
    )),
    "order_video": ("Tong", "Buyruq: video raport", ("day", "phrase", "deadline", "minutes"), (
        "📣 <b>BUYRUQ №{day}</b>\n\n"
        "Ovoz chiqarib o'qing:\n<blockquote>{phrase}</blockquote>\n"
        "📍 Tashqariga (ko'cha yoki hovliga) chiqing.\n"
        "🎥 <b>Video krujok</b> yozing: kamera atrofga qaragan, yurib turib gapni o'qing.\n\n"
        "⏱ Muddat: <b>{deadline}</b> gacha."
    )),
    "order_female_hint": ("Tong", "Video: qizlar uchun izoh", (), (
        "<i>Yuzingizni ko'rsatish shart emas — orqa kamerani yoqing, ovozingiz eshitilsin.</i>"
    )),
    "voice_ok": ("Tong", "Ovozli raport qabul qilindi", ("day",), "✅ Raport qabul qilindi. {day}-kun bajarildi. Rotangizga e'lon qilindi."),
    "video_sent": ("Tong", "Video tekshiruvga yuborildi", (), (
        "✅ Video qabul qilindi. Rotadoshlaringizdan {reviewers} kishi tekshiradi — natija keladi."
    )),
    "squad_post": ("Tong", "Rota guruhidagi raport sarlavhasi", ("icon", "name", "day"), "{icon} <b>{name}</b> — {day}-kun raporti"),
    "review_request": ("Tong", "Video tekshiruv so'rovi", ("name", "day", "phrase"), (
        "🔍 <b>TEKSHIRUV</b> · {name}, {day}-kun\n\n"
        "O'qilishi kerak bo'lgan gap:\n<blockquote>{phrase}</blockquote>\n"
        "Shartlar: tashqarida yozilgan, gap aniq o'qilgan.\nHalol baho bering."
    )),
    "vote_thanks": ("Tong", "Ovoz berilgani uchun rahmat", (), "Ovozingiz hisobga olindi."),
    "video_approved": ("Tong", "Video tasdiqlandi", ("day",), "✅ Rota videongizni tasdiqladi. {day}-kun yopildi. Zo'r!"),
    "video_rejected": ("Tong", "Video rad etildi", (), "❌ Rota videongizni tasdiqlamadi. Bu kun bajarilmagan hisoblanadi."),
    "unknown_media": ("Tong", "Noto'g'ri fayl yuborildi", (), "Raport uchun ovozli xabar yuboring."),

    # --- Jazo va mukofot ---
    "strike": ("Jazo", "Ogohlantirish (shaxsan)", ("count", "reason"), (
        "⚠️ <b>OGOHLANTIRISH {count}/{max_strikes}</b> — {reason}.\nSen o'zgaraman deb kelganding. Qani harakat!"
    )),
    "strike_last": ("Jazo", "Oxirgi ogohlantirish oldidan", ("count", "reason"), (
        "⚠️ <b>OGOHLANTIRISH {count}/{max_strikes}</b> — {reason}.\nYana bitta xato — lagerdan chiqasan. Ertaga isbotla."
    )),
    "strike_public": ("Jazo", "Ogohlantirish (rota guruhiga)", ("name", "count", "reason"), (
        "⚠️ <b>{name}</b> — ogohlantirish {count}/{max_strikes} ({reason})."
    )),
    "reason_late": ("Jazo", "Sabab: kech turdi", (), "vaqtida turmadi"),
    "reason_no_voice": ("Jazo", "Sabab: ovozli raport yo'q", (), "ovozli raport yo'q"),
    "reason_no_video": ("Jazo", "Sabab: video yo'q", (), "video raport yo'q"),
    "reason_rejected": ("Jazo", "Sabab: rota rad etdi", (), "rota tasdiqlamadi"),
    "reason_admin": ("Jazo", "Sabab: admin qarori", (), "qo'mondonlik qarori"),
    "immunity_used": ("Jazo", "Immunitet ishlatildi", ("reason",), (
        "🛡 Immunitet seni qutqardi ({reason}). Ogohlantirish o'chirildi — endi ehtiyot bo'l."
    )),
    "immunity_referral": ("Jazo", "Immunitet: do'st taklifi", (), (
        "🛡 Do'stingiz qabul qilindi — sizga 1 ta Immunitet! U keyingi ogohlantirishni o'chiradi."
    )),
    "immunity_sunday": ("Jazo", "Immunitet: yakshanba", (), (
        "🛡 Yakshanba ham barvaqt turding! Mukofot — 1 ta Immunitet. Men senga ishonaman!"
    )),
    "immunity_admin": ("Jazo", "Immunitet: qo'mondonlik", (), "🛡 Qo'mondonlik sizga 1 ta Immunitet berdi."),
    "expelled": ("Jazo", "Lagerdan chiqarildi (shaxsan)", (), (
        "🚫 {max_strikes} ta ogohlantirish. Nizom hamma uchun bir xil — siz lagerdan chiqarildingiz.\n"
        "Bu oxiri emas. Keyingi oqimda qaytib, isbotlab ko'rsating."
    )),
    "expelled_public": ("Jazo", "Lagerdan chiqarildi (rota guruhiga)", ("name",), (
        "🚫 <b>{name}</b> {max_strikes} ta ogohlantirish oldi va lagerdan chiqarildi."
    )),
    "stage_up": ("Jazo", "Yangi bosqich", ("name", "day", "description"), (
        "🏅 <b>{name}</b>! Siz {day} kunni ortda qoldirdingiz.\n{description}\n\n"
        "Hozir qanchalik qiyin bo'lmasin, sen zo'r ketyapsan. Men senga ishonaman!"
    )),

    # --- Rota guruhi ---
    "chat_open_morning": ("Rota", "Tonggi oyna ochildi", (), "🌅 <b>Tonggi oyna ochildi.</b> Saf torting! Uxlab qolganlarni uyg'oting."),
    "chat_open_evening": ("Rota", "Kechki oyna ochildi", (), (
        "🌙 <b>Kechki oyna ochildi.</b> Bugungi kun qanday o'tdi? Refleksiya — Mini App'da."
    )),
    "chat_closed": ("Rota", "Oyna yopildi", (), "🔒 Oyna yopildi. Keyingi oynada ko'rishamiz."),
    "roll_call_header": ("Rota", "Tonggi raport sarlavhasi", ("squad", "day"), "📋 <b>TONGGI RAPORT</b> · {squad} · {day}-kun"),
    "roll_call_footer": ("Rota", "Tonggi raport yakuni", ("done", "total"), "Safda: <b>{done}/{total}</b>"),
    "roll_call_all_done": ("Rota", "Butun rota bajardi", (), "Butun rota saf tortdi. Mana bu — intizom! 💪"),
    "squad_invite": ("Rota", "Rota guruhiga taklif", ("squad", "link"), "🎖 Rotangiz guruhi tayyor: <b>{squad}</b>\nKirish: {link}"),
    "join_denied": ("Rota", "Guruhga kirish rad etildi", (), "Bu guruh faqat shu rota a'zolari uchun."),
}

PHRASES = [
    "Men bugun o'z irodamning xo'jayiniman.",
    "Intizom — bu o'zimga bergan va'damni bajarish.",
    "Har bir erta tong — kelajagimga qo'yilgan sarmoya.",
    "Qiyinchilik vaqtinchalik, odat esa umrbod qoladi.",
    "Ko'rpa meni yengolmaydi. Men turdim va harakatdaman.",
    "Bugun kechagidan bir qadam kuchliroqman.",
    "Bahona emas, natija. Men uyg'oqman va tayyorman.",
    "Erta turgan yutadi. Bugun men yutaman.",
    "O'zgarish bugun, aynan shu daqiqada boshlanadi.",
    "Men rotamni tushirib qo'ymayman. Men shu yerdaman.",
    "Uyqum emas, maqsadim meni boshqaradi.",
    "Har tong — yangi imkoniyat. Uni qo'ldan bermayman.",
]

STAGES = [
    # (kun, nom, tavsif, ikonka)
    (3, "Omon qolgan", "Tananing shoki ortda. Vaqtida turish va ovozli raport odatga aylanmoqda.", "sprout"),
    (7, "Moslashgan", "Tana yangi rejimga moslashdi. Budilnik har kuni oldinga surilmoqda.", "mountain"),
    (21, "Temir Iroda", "Qat'iy rejim. Odat shakllandi — endi bu sizning hayotingiz.", "shield"),
    (40, "Yengilmas / Mentor", "Eng kuchlilar. Keyingi oqimlarda yangilarni tekshirasiz va ustoz bo'lasiz.", "crown"),
]
