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
        "<b>Qanday ishlaydi:</b>\n"
        "• O'zingizga mos <b>rotani</b> (uyg'onish jamoasi, 7 kishi) tanlaysiz\n"
        "• Har tong o'z vaqtida bot uyg'otadi — «Uyg'ondim» bosasiz\n"
        "• {voice_deadline} daqiqa ichida bot bergan gapni ovoz chiqarib o'qib, <b>ovozli raport</b> yuborasiz\n"
        "• <b>Budilnik asta erta tortadi:</b> masalan 07:00 → 05:30 degani — 1-kun 07:00 da turasiz, "
        "{shift_from_day}-kundan har kuni {shift_step} daqiqa <b>ertaroq</b>, 05:30 ga silliq yetguncha\n"
        "• Bosqichlarda <b>pogon, medal va sertifikat</b> olasiz\n"
        "• {max_strikes} ta ogohlantirish — lagerdan chiqarilasiz\n\n"
        "Arizani to'ldiramiz — 1 daqiqa vaqt oladi."
    )),
    "registration_closed": ("Ariza", "Qabul yopiq", (), (
        "Hozircha ariza qabul qilinmayapti. Keyingi oqim e'lon qilinishini kuting."
    )),
    "ask_first_name": ("Ariza", "1-savol: ism", (), "<b>1/6.</b> Ismingiz?"),
    "ask_last_name": ("Ariza", "2-savol: familiya", (), "<b>2/6.</b> Familiyangiz?"),
    "bad_name": ("Ariza", "Ism/familiya xato", (), "Iltimos, to'g'ri yozing: 2–30 ta harf."),
    "ask_region": ("Ariza", "3-savol: viloyat", (), "<b>3/6.</b> Qaysi viloyatdansiz?"),
    "ask_gender": ("Ariza", "4-savol: jins", (), (
        "<b>4/6.</b> Jinsingiz?\n<i>Yigitlar va qizlar alohida rotalarda bo'ladi.</i>"
    )),
    "ask_goal": ("Ariza", "5-savol: maqsad", (), (
        "<b>5/6.</b> Nima uchun keldingiz? Maqsadingizni bir-ikki gap bilan yozing.\n"
        "<i>Masalan: «Har kuni erta turib, bomdod va sportni qoldirmayman.»</i>"
    )),
    "goal_too_short": ("Ariza", "Maqsad juda qisqa", (), "Bu maqsad emas, bu bahona. Kamida 10 belgi — aniqroq yozing."),
    "ask_slot": ("Ariza", "6-savol: rotani tanlash", ("cohort", "start_date", "days_left"), (
        "<b>6/6.</b> Rotangizni tanlang 👇\n\n"
        "📅 Oqim: <b>{cohort}</b> · start <b>{start_date}</b> (lager {days_left} kundan boshlanadi)\n\n"
        "Har bir tugma — <b>boshlang'ich vaqt → maqsad vaqti</b>.\n"
        "Masalan <b>07:00 → 05:30</b>: birinchi kun 07:00 da turasiz, {shift_from_day}-kundan har kuni "
        "{shift_step} daqiqa erta — oxirida 05:30 da. Shunday qilib tanangiz silliq moslashadi.\n\n"
        "O'zingiz bemalol turadigan vaqtni tanlang — keyin o'zgarmaydi."
    )),
    "no_slots": ("Ariza", "Ochiq rota yo'q", (), (
        "Hozircha ochiq rota yo'q. Yangi oqim e'lon qilinishi bilan xabar beramiz."
    )),
    "application_summary": ("Ariza", "Arizani tasdiqlash", ("full_name", "region", "gender", "goal", "slot", "start_date"), (
        "📝 <b>Arizangiz</b>\n\n"
        "Ism-familiya: <b>{full_name}</b>\nViloyat: {region}\nJins: {gender}\n"
        "Rota: <b>{slot}</b>\nStart: {start_date}\n"
        "Maqsad: <i>{goal}</i>\n\n"
        "Hammasi to'g'rimi? Yuborilgandan keyin jinsni o'zgartirib bo'lmaydi."
    )),
    "submitted": ("Ariza", "Ariza yuborildi", (), (
        "✅ Ariza qo'mondonlikka yuborildi.\n"
        "Tasdiqlangach, rotangiz, start sanasi va lager qoidalari keladi.\n\n"
        "Endi eng muhimi 👇"
    )),
    "manifest_caption": ("Ariza", "Taklif rasmi ostidagi matn", ("link",), (
        "🤝 <b>Yolg'iz bo'lma — rota bo'lib harakat qil!</b>\n\n"
        "Erta turish birga osonroq. Bu rasmni storisga joylang yoki do'stingizga yuboring — "
        "u ham shu havola orqali qo'shilsin:\n{link}"
    )),
    "referral_share": ("Ariza", "Do'st taklifi havolasi (menyu tugmasi)", ("link",), (
        "🤝 <b>Yolg'iz bo'lma — do'stingni chaqir!</b>\n\n"
        "Birga erta turish osonroq. Ushbu havolani do'stingga yubor — u shu orqali qo'shilsin:\n{link}"
    )),
    "already_pending": ("Ariza", "Ariza ko'rib chiqilmoqda", (), "⏳ Arizangiz ko'rib chiqilmoqda. Sabr — bu ham intizom."),
    "rejected": ("Ariza", "Ariza rad etildi", (), "Afsus, bu safar arizangiz qabul qilinmadi. Keyingi oqimda yana urinib ko'ring."),
    "not_registered": ("Ariza", "Ro'yxatdan o'tmagan", (), "Avval ariza qoldiring: /start"),
    "approved": ("Ariza", "Qabul qilindi (rotaga joylashdi)",
                 ("name", "cohort", "start_date", "days_left", "tribe", "squad", "alarm", "target"), (
        "🎖 <b>QABUL QILINDINGIZ, {name}!</b>\n\n"
        "Oqim: <b>{cohort}</b>\n"
        "Start: <b>{start_date}</b> ({days_left} kun qoldi)\n"
        "Rota: <b>{squad}</b> · {tribe}\n"
        "Birinchi budilnik: <b>{alarm}</b> → maqsad {target}\n\n"
        "Rotangiz bilan muloqot va raportlar — <b>Mini App</b> ichidagi rota chatida.\n\n"
        "Quyida — raport qanday yuborilishi. Diqqat bilan o'qing 👇"
    )),
    "approved_waiting": ("Ariza", "Qabul qilindi (oqim hali yo'q)", (), (
        "🎖 <b>QABUL QILINDINGIZ!</b>\nYangi oqim e'lon qilinganda /join orqali rotani tanlaysiz. Kuzatib boring."
    )),
    "welcome_back": ("Ariza", "Holat (/holat)", ("name", "tribe", "squad", "strikes", "immunities"), (
        "🎖 {name}, saf tortish joyingiz:\n"
        "{tribe} · <b>{squad}</b>\n"
        "Ogohlantirishlar: {strikes}/{max_strikes} · Immunitet: {immunities}\n\n"
        "Buyruqlar: /holat — holat, /yoriqnoma — raport qanday yuboriladi, /nizom — lager qoidalari"
    )),
    "guide": ("Ariza", "Yo'riqnoma (/yoriqnoma)", (), (
        "📘 <b>YO'RIQNOMA — har tong nima qilasiz</b>\n\n"
        "1️⃣ Budilnik vaqtida bot sizga ⏰ <b>TURISH!</b> xabarini yuboradi.\n"
        "2️⃣ Xabar ostidagi <b>«☀️ Uyg'ondim»</b> tugmasini bosing — {wake_grace} daqiqa ichida.\n"
        "3️⃣ Bot <b>BUYRUQ</b> va bugungi gapni yuboradi.\n"
        "4️⃣ Gapni <b>shu botga ovozli xabar</b> qilib yuboring — budilnikdan keyin {voice_deadline} daqiqa ichida:\n"
        "     • pastki o'ng burchakdagi 🎙 <b>mikrofon</b> tugmasini bosib turing\n"
        "     • gapni ovoz chiqarib, aniq o'qing\n"
        "     • barmog'ingizni qo'yib yuboring — xabar o'zi ketadi\n"
        "     <i>Mikrofon o'rnida 📷 ko'rinsa — unga bir marta bosing, 🎙 ga almashadi.</i>\n"
        "5️⃣ Bot «✅ Raport qabul qilindi» deydi — kuningiz yozildi.\n\n"
        "❗ Raportni <b>shu botga</b> yuboring. U <b>Mini App</b> ichidagi rota chatida paydo bo'ladi — "
        "rotadoshlaringiz eshitadi va ko'radi.\n\n"
        "🎯 <b>Hozir mashq qiling:</b> istalgan gapni ovozli xabar qilib shu yerga yuboring."
    )),
    "practice_ok": ("Ariza", "Mashq raporti qabul qilindi", ("start_date", "days_left", "alarm"), (
        "✅ <b>Zo'r! Mashq raporti qabul qilindi.</b>\n"
        "Start kuni aynan shunday yuborasiz. Start: <b>{start_date}</b> ({days_left} kun qoldi), birinchi budilnik <b>{alarm}</b>."
    )),
    "practice_waiting": ("Ariza", "Mashq (oqim hali yo'q)", (), (
        "✅ Mashq raporti qabul qilindi. Oqim boshlanganda aynan shunday yuborasiz."
    )),
    "countdown": ("Ariza", "Startgacha eslatma (har kech)", ("days_left", "start_date", "squad", "alarm"), (
        "⏳ Startga <b>{days_left} kun</b> qoldi ({start_date}).\n"
        "Rota: {squad} · birinchi budilnik <b>{alarm}</b>.\nBugundan erta yotishni odat qiling."
    )),
    "countdown_tomorrow": ("Ariza", "Startdan bir kun oldin", ("alarm", "squad"), (
        "🔥 <b>ERTAGA START!</b>\n\n"
        "Birinchi budilnik: <b>{alarm}</b> · {squad}\n"
        "Bugun erta yoting va telefon ovozini yoqib qo'ying.\n"
        "Bot «TURISH!» deb yozadi — «Uyg'ondim»ni bosing va ovozli raport yuboring. Omad, jangchi!"
    )),
    "rules": ("Ariza", "Lager nizomi (/nizom)", (), (
        "📜 <b>LAGER NIZOMI</b>\n\n"
        "<b>1. Turish.</b> Budilnikdan keyin {wake_grace} daqiqa ichida «Uyg'ondim» tugmasini bosing.\n"
        "<b>2. Raport.</b> Bot bergan gapni ovoz chiqarib o'qing va budilnikdan keyin {voice_deadline} daqiqa ichida "
        "shu botga <b>ovozli xabar</b> yuboring.\n"
        "<b>3. Kaizen.</b> {shift_from_day}-kundan budilnik har kuni {shift_step} daqiqa oldinga suriladi — maqsad vaqtigacha.\n"
        "<b>4. Rota.</b> {squad_size} kishilik rotada yashaysiz. Raportingiz Mini App'dagi rota chatida ko'rinadi.\n"
        "<b>5. Oynalar.</b> Rota chatiga faqat tong va kechqurun belgilangan vaqtda yozasiz — qolgan vaqt kuzatasiz.\n"
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
    "voice_ok": ("Tong", "Ovozli raport qabul qilindi", ("day",), "✅ Raport qabul qilindi. {day}-kun bajarildi. Rota chatida ko'rindi."),
    "video_sent": ("Tong", "Video tekshiruvga yuborildi", (), (
        "✅ Video qabul qilindi. Rotadoshlaringizdan {reviewers} kishi tekshiradi — natija keladi."
    )),
    "review_request": ("Tong", "Video tekshiruv so'rovi", ("name", "day", "phrase"), (
        "🔍 <b>TEKSHIRUV</b> · {name}, {day}-kun\n\n"
        "Rotadoshingiz yurish videosini yubordi. 📱 <b>«Rota»</b> bo'limiga kiring — videoni ko'ring "
        "va «Tasdiqlayman / Rad etaman» tugmasini bosing.\n\n"
        "O'qilishi kerak bo'lgan gap:\n<blockquote>{phrase}</blockquote>"
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
    "award_caption": ("Jazo", "Bosqich mukofoti (rasm ostida)",
                      ("name", "stage", "day", "rank", "award", "description", "number"), (
        "🎖 <b>{name}, tabriklaymiz!</b>\n\n"
        "Siz <b>{day} kun</b>ni ortda qoldirdingiz va «<b>{stage}</b>» bosqichiga chiqdingiz.\n"
        "{description}\n\n"
        "Mukofot: <b>{award}</b> · {rank}\nRaqam: <code>{number}</code>\n\n"
        "Hozir qanchalik qiyin bo'lmasin, sen zo'r ketyapsan. Men senga ishonaman!"
    )),

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
    # (kun, nom, tavsif, ikonka, mukofot turi, harbiy unvon, pogondagi yulduzlar)
    (3, "Omon qolgan", "Tananing shoki ortda. Vaqtida turish va ovozli raport odatga aylanmoqda.", "sprout", "pagon", "Oddiy askar", 1),
    (7, "Moslashgan", "Tana yangi rejimga moslashdi. Budilnik har kuni oldinga surilmoqda.", "mountain", "medal", "Kichik serjant", 2),
    (21, "Temir Iroda", "Qat'iy rejim. Odat shakllandi — endi bu sizning hayotingiz.", "shield", "certificate", "Serjant", 3),
    (40, "Yengilmas / Mentor", "Eng kuchlilar. Keyingi oqimlarda yangilarni tekshirasiz va ustoz bo'lasiz.", "crown", "certificate", "Leytenant", 4),
]
