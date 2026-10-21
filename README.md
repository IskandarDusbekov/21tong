# 21tong

Odamlarning uyqu va hayot rejimini to'g'rilovchi, qat'iy intizomga asoslangan 21 kunlik onlayn lager.
Telegram Bot + Telegram Mini App (React) + Django/PostgreSQL.

## Tuzilma

```
backend/            Django + DRF — barcha biznes-qoidalar shu yerda
  apps/accounts/    User (telegram_id, jins, maqsad, ariza vaqtlari, referral), Manifest rasmi, auth
  apps/camp/        Oqim, Qabila, Rota (7 kishi), Ishtirok, Kunlik yozuv, Strike, Joker, Muzlatish, outbox
    rules.py        Lager raqamlari va sof funksiyalar (Kaizen, bosqichlar, kvorum, gaplar...)
    services.py     Holatni o'zgartiruvchi yagona joy (bot ham, Mini App ham shu orqali)
  apps/proofs/      Video raport va P2P tekshiruv (avval rotadan, faqat bir jinsdagilar)
  apps/community/   Rota chati, kechki refleksiya, 🔥, Bounty, IrodaCoin, tonggi rasm chelenji, reyting
  apps/control/     Admin paneldan boshqariladigan sozlamalar, gaplar, bosqichlar, bot matnlari, ommaviy xabar
  apps/api/         /api/bot/* (X-Bot-Secret) va /api/app/* (Telegram initData)
bot/                aiogram 3 — ariza, admin tasdig'i, buyruqlar, raportlar, budilnik
miniapp/            React + Vite — Bugun / Rota (chat) / Yo'l / Bounty / Reyting
panel/              React + Vite — admin uchun boshqaruv paneli (/panel/)
```

Bot hech qanday qoidani o'zi hal qilmaydi: u backend'ga so'rov yuboradi va `Notification` navbatidagi
voqealarni (ariza, ogohlantirish, joker, tekshiruv...) Serjant/Murabbiy ohangida yetkazadi (`bot/texts.py`).

## Boshqaruv paneli — kundalik ish uchun

http://localhost:8000/panel/ — Django admin'dan tashqari, sodda va chiroyli panel (kompyuter va telefon).
Kirish — admin login va parolingiz (`createsuperuser` bilan yaratilgan, `is_staff` bo'lishi kerak).

- **Bosh sahifa** — bugungi ko'rsatkichlar, oqim grafigi (kunlar bo'yicha bajardi / ogohlantirish / dam),
  rotalarning tonggi raporti, yangi arizalar va so'nggi voqealar.
- **Arizalar** — bir bosishda qabul qilish / rad etish.
- **Ishtirokchilar** — qidiruv va filtrlar; har bir odam uchun 21 kunlik kalendar, ogohlantirishlar,
  Immunitet berish, ogohlantirish berish/bekor qilish, chiqarish/qaytarish, rotani o'zgartirish,
  bajarilmagan kunni uzrli qilish.
- **Rotalar** — har rota kim turdi, kim yo'q (rota muloqoti Mini App ichidagi chatda).
- **Video raportlar**, **Oqimlar** (yaratish, qabulni ochish, boshlash, yakunlash), **Ommaviy xabar**
  (oldindan ko'rish va qabul qiluvchilar soni bilan).
- **Lager qoidalari** — barcha sozlamalar va ularning amalda qanday ishlashini ko'rsatuvchi jonli misol.
- **Bot matnlari** — Telegram ko'rinishidagi jonli oldindan ko'rish bilan; **Gaplar va bosqichlar**.

Panel kodi o'zgarsa:

```bash
cd panel && npm install && npm run build
```

Tez ishlab chiqish uchun `npm run dev` (http://localhost:5174/panel/, API Django'ga proxy qilinadi).

## Django admin — texnik boshqaruv

http://localhost:8000/admin/ — bosh sahifada bugungi holat: yangi arizalar, raport berganlar, ogohlantirishlar
va tezkor havolalar.

| Bo'lim | Nima qilish mumkin |
|---|---|
| **Boshqaruv → Lager sozlamalari** | Barcha qoidalar: «Uyg'ondim» va raport muddatlari, budilnik qaysi kundan va necha daqiqaga suriladi, video qaysi kundan (0 — umuman yo'q), nechta ogohlantirishda chiqariladi, rota hajmi, yakshanba, Immunitet, muzlatish, ariza qabul qilish, yangi oqim uchun oynalar |
| **Boshqaruv → Bot xabarlari** | Botning har bir xabar matni. Har sahifada ishlatish mumkin bo'lgan `{o'zgaruvchilar}` va standart matn ko'rsatiladi; noto'g'ri o'zgaruvchi saqlanmaydi; "Standartga qaytarish" amali bor. Bot o'zgarishni 30 soniyada oladi |
| **Boshqaruv → O'qiladigan gaplar** | Uyg'ongach o'qiladigan gaplar ro'yxati (qo'shish, o'chirish, faol/nofaol) |
| **Boshqaruv → Bosqichlar** | 3/7/21/40-kun bosqichlari: kun, nom, tavsif, ikonka |
| **Boshqaruv → Ommaviy xabar** | Hammaga / oqimga / rotaga / faqat qizlar yoki yigitlarga xabar — saqlash bilan darhol yuboriladi |
| **Foydalanuvchilar** | Arizalarni qabul qilish / rad etish, Immunitet berish |
| **Lager → Oqimlar** | Oqim ochish, qabulni ochish, boshlash, yakunlash, kunlik jarayonni qo'lda ishga tushirish |
| **Lager → Ishtirokchilar** | Immunitet berish, ogohlantirish berish, oxirgi ogohlantirishni bekor qilish, chiqarish, qaytarish, Mentor qilish, rotasini o'zgartirish |
| **Lager → Kunlik yozuvlar** | Kunni uzrli deb belgilash (ogohlantirish ham bekor bo'ladi), qo'lda baholash |
| **Raportlar → Video raportlar** | Videoni qo'lda tasdiqlash / rad etish |

## Lager qanday ishlaydi

**Oqim va tayyor rotalar.** Admin panelda (Oqimlar) oqim ochiladi va **aniq start sanasi** qo'yiladi
(masalan 3 kundan keyin). Har oqimga 3–4 ta **tayyor rota vaqti** qo'shiladi, masalan `06:00 → 05:00`.
"Keyingi oqim (+7 kun)" tugmasi shu vaqtlar bilan har haftalik yangi qabulni bir bosishda ochadi.

**Ariza.** `/start` → ism → familiya → viloyat (ro'yxatdan) → jins → maqsad → **tayyor rotani tanlash** →
tasdiqlash → storis uchun taklif rasmi ("Yolg'iz bo'lma — rota bo'lib harakat qil", QR-kod bilan).
Ariza `ADMIN_IDS` dagi adminlarga **"✅ Qabul / ❌ Rad"** tugmalari bilan keladi (yoki panelda / `/arizalar`).
Qabul qilinganda odam tanlagan rotasiga joylashadi; bot unga start sanasi, birinchi budilnik va
**yo'riqnoma** yuboradi: raport qayerga va ovozli xabar qanday yuboriladi. Startgacha **mashq raporti**
yuborib ko'rish mumkin, har kech 20:00 da "Startga N kun qoldi" eslatmasi keladi.

**Mukofotlar.** Har bosqichda bot ism-familiya, viloyat, sana va raqam bilan rasm yuboradi: **pogon** (harbiy
unvon, yulduzlar bilan), **medal** yoki **sertifikat** — qaysi bosqichga qaysi mukofot berilishini admin tanlaydi
(Gaplar va bosqichlar). Mukofotlar Mini App'ning "Yo'l" bo'limida ham ko'rinadi.

Do'st taklifi Immunitet bermaydi (sozlamada yoqish mumkin).

**Har tong:**

1. Budilnik vaqtida bot `TURISH!` xabarini **«☀️ Uyg'ondim»** tugmasi bilan yuboradi (Mini App'da ham bor).
2. Bosilgach bot **BUYRUQ** beradi: bugungi tasodifiy gap (har kuni har kimga boshqa — eski yozuvni qayta yuborib bo'lmaydi).
3. Gap o'qilgan **ovozli raport botga** (shaxsiy chatga), budilnikdan keyin **5 daqiqa** ichida yuboriladi.
   Admin panelda video yoqilsa (masalan 7-kundan) — o'sha kundan tashqarida yozilgan video krujok so'raladi,
   uni rotadan 3 kishi gap bilan solishtirib tekshiradi.
4. Budilnik **3-kundan** boshlab har kuni 5 daqiqaga oldinga suriladi — maqsad vaqtigacha.
5. Raport **Mini App ichidagi rota chatida** paydo bo'ladi — rotadoshlar ovozni eshitadi, videoni ko'radi.
   Admin tekshirsa «Admin tekshirdi» yozuvi hammaga ko'rinadi. Kech kelgan raport ham chatga tushadi, lekin
   «qabul qilinmadi» deb belgilanadi va kun bajarilgan hisoblanmaydi. Chat sarlavhasida safda nechta (X/Y) turibdi.

**Jazo.** Bajarmaslik — ogohlantirish (rota chatida ham ko'rinadi). 3 ta — lagerdan chiqariladi.
**Immunitet** (avvalgi "Joker") keyingi ogohlantirishni o'chiradi: yakshanba barvaqt turganlarga, do'st taklif qilganlarga
yoki qo'mondonlik tomonidan beriladi.

**Tonggi rasm chelenji.** Har kuni «Bounty» bo'limida — har kishi 2 tagacha rasm yuboradi, qabiladoshlar 🔥 beradi,
eng ko'p ovoz olgan rasm yuqoriga chiqadi. Olingan ovozlar reytingga ta'sir qiladi.

**Reyting (3 daraja).** «Reyting» bo'limida: (1) **Rotam** — rota ichidagi shaxslar, (2) **Rotalar** — rotalar o'rtasida
(o'rtacha ball bo'yicha), (3) **Eng zo'rlar** — butun qabila bo'yicha eng kuchlilar. Ball = bajarilgan kun·10 +
IrodaCoin + rasm chelenjidagi 🔥·5.

Yuqoridagi barcha raqamlar standart qiymatlar — admin panelda o'zgartiriladi.

## Konsepsiya → kod

| Konsepsiya | Qayerda |
|---|---|
| Jins birinchi so'raladi, keyin o'zgarmaydi | `services.register_user` |
| Ariza va admin tasdig'i (Telegram'da) | `bot/handlers/onboarding.py`, `bot/handlers/admin.py`, `services.approve_user` |
| 7 kishilik rota | `rules.SQUAD_SIZE`, `services.assign_squad` |
| Manifest + do'st taklifi → 1 Immunitet | `accounts/manifest.py`; Joker do'st **tasdiqlanganda** beriladi |
| Gender-izolyatsiya | Qabila `(oqim, jins, vaqt)`; rota chati faqat o'z rotasiga ko'rinadi |
| Kaizen −5 daqiqa | `rules.alarm_time_for_day` |
| Uyg'ondim → gap → raport | `services.press_wake`, `record_voice`, `proofs.submit_video` |
| 3 tadan 2 tasi tasdiqlasa | `proofs.services.cast_vote`, `rules.approval_threshold` |
| Oynalar 05:30–07:30, 20:30–21:30 | `Cohort` maydonlari; chatga yozish faqat oyna ochiqligida (server tekshiradi) |
| Tonggi raport | `services.squad_report`, `bot/tasks.py` |
| 3 ogohlantirish = chiqarish, Immunitet o'chiradi | `services.issue_strike` |
| Yakshanba: ogohlantirish yo'q, bajarsa Immunitet | `services.evaluate_day` |
| Muzlatish: 1 marta, faqat kechqurun ertangi kun uchun | `services.request_freeze` |
| Bosqichlar 3/7/21/40 | Admin → Bosqichlar (`control.Stage`) |
| Barcha raqamlar | Admin → Lager sozlamalari (`control.CampSettings`), `camp/rules.py` |

### Standart qarorlar (admin panelda o'zgaradi)

- «Uyg'ondim» — budilnikdan keyin **5 daqiqa**, ovozli raport — **5 daqiqa** ichida.
- Budilnik **3-kundan** har kuni **5 daqiqaga** suriladi.
- Video raport **o'chiq** (har kuni ovozli raport).
- **Immunitet** keyingi ogohlantirishda avtomatik ishlatiladi.
- Kun oxirigacha hech kim ovoz bermagan video — tasdiqlangan hisoblanadi.
- Muzlatish oqimda **1 marta**, **18:00** dan keyin.
- Do'st taklifi uchun Immunitet do'st admin tomonidan qabul qilinganda beriladi.

## Lokal ishga tushirish

```bash
cp .env.example .env
```

Backend (venv allaqachon bor):

```bash
cd backend && ../venv/Scripts/python -m pip install -r requirements.txt && ../venv/Scripts/python manage.py migrate && ../venv/Scripts/python manage.py createsuperuser
```

```bash
cd backend && ../venv/Scripts/python manage.py runserver
```

### Botni ishga tushirish

1. [@BotFather](https://t.me/BotFather) da bot yarating va tokenni `.env` dagi `TELEGRAM_BOT_TOKEN` ga yozing.
2. O'z Telegram ID'ingizni [@userinfobot](https://t.me/userinfobot) dan oling va `.env` ga yozing: `ADMIN_IDS=123456789`
   (bir nechta admin bo'lsa vergul bilan).
3. `runserver` ishlab turgan bo'lsin, keyin **ikkinchi terminalda**:

```bash
cd bot && ../venv/Scripts/python main.py
```

"Bot ishga tushdi: @..." chiqsa — tayyor. Botga `/start` yozib arizani sinab ko'ring; ariza sizga tugmalar bilan keladi.

**Rota chati:** Telegram guruh kerak emas — rota muloqoti, raportlar va tonggi raport **Mini App ichidagi
«Rota» bo'limida**. Chatga yozish faqat tonggi va kechki oyna vaqtida ochiq; qolgan vaqt faqat kuzatiladi.
Kechki refleksiya ham shu chatda — kechqurun «Bugungi kun qanday o'tdi?» deb so'raladi, rotadoshlar 🔥 beradi.

**Bot pastki menyu:** qabul qilingan foydalanuvchiga doimiy tugmalar chiqadi — 📱 Mini App · ☀️ Holatim ·
📘 Yo'riqnoma · 📜 Nizom · 👥 Do'st taklif. Har biri aniq amal bajaradi.

**Mini App his-tuyg'usi:** «Uyg'ondim» marosimi (quyosh portlashi), bosqich ochilishi va chat animatsiyalari;
yengil ovoz belgilari (yuqori o'ngdagi 🔊 tugmasi bilan o'chiriladi). `prefers-reduced-motion` hurmat qilinadi.

### Telegram'siz brauzerda ko'rish (Dev kirish)

`DEBUG=true` bo'lganda Mini App'ni oddiy brauzerda, demo foydalanuvchi sifatida ochish mumkin:

```bash
cd miniapp && npm install && npm run build
```

```bash
cd backend && ../venv/Scripts/python manage.py seed_demo --reset
```

Keyin `runserver` ni ishga tushiring va oching:

- http://localhost:8000/ — Mini App, "Dev kirish" ekranidan foydalanuvchi tanlanadi
- http://localhost:8000/admin/ — admin panel (`createsuperuser` bilan yaratilgan login)

Dev kirish `Authorization: dev <telegram_id>` sarlavhasi orqali ishlaydi va `DEBUG=false` da
(yoki `DEV_LOGIN=false`) butunlay o'chadi. Mini App kodi o'zgarsa — `npm run build` ni qayta bajaring
yoki tez yangilanish uchun `npm run dev` (http://localhost:5173) dan foydalaning.

Mini App'ni Telegram ichida ochish uchun HTTPS manzil kerak (`MINI_APP_URL`). Lokal sinovda shart emas —
«Uyg'ondim» tugmasi botning o'zida ham bor.

Kunlik hisob (kechagi kunlarni baholash, start sanasi kelgan oqimni boshlash) — **cron shart emas**:
bot uni har kecha 00:05 da va har ishga tushganda o'zi chaqiradi. Qo'lda ishga tushirish:

```bash
cd backend && ../venv/Scripts/python manage.py run_daily
```

Mukofot va taklif rasmlari tizim shriftlari bilan chiziladi (Windows: Segoe UI / Georgia, Linux serverda:
`fonts-dejavu` paketi). Boshqa shrift ishlatish uchun `.env` da `MANIFEST_FONT_DIR` ni ko'rsating.

Testlar:

```bash
cd backend && ../venv/Scripts/python manage.py test apps
```
