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
  apps/community/   Kechki refleksiya, 🔥, Bounty, IrodaCoin
  apps/api/         /api/bot/* (X-Bot-Secret) va /api/app/* (Telegram initData)
bot/                aiogram 3 — ariza, admin tasdig'i, buyruqlar, raportlar, budilnik, rota guruhlari
miniapp/            React + Vite — Bugun / Yo'l / Lenta / Bounty / Reyting
```

Bot hech qanday qoidani o'zi hal qilmaydi: u backend'ga so'rov yuboradi va `Notification` navbatidagi
voqealarni (ariza, ogohlantirish, joker, tekshiruv...) Serjant/Murabbiy ohangida yetkazadi (`bot/texts.py`).

## Lager qanday ishlaydi

**Ariza.** `/start` → jins → maqsad → hozir turadigan vaqt → maqsad vaqti → tasdiqlash → manifest rasmi.
Ariza `ADMIN_IDS` dagi adminlarga **"✅ Qabul / ❌ Rad"** tugmalari bilan keladi (yoki `/arizalar`).
Qabul qilinsa va qabul ochiq oqim bo'lsa, foydalanuvchi o'zi qabila va **7 kishilik rotaga** joylashadi.

**Har tong:**

1. Budilnik vaqtida bot `TURISH!` xabarini **«☀️ Uyg'ondim»** tugmasi bilan yuboradi (Mini App'da ham bor).
2. Bosilgach bot **BUYRUQ** beradi: bugungi tasodifiy gap (har kuni har kimga boshqa — eski yozuvni qayta yuborib bo'lmaydi).
3. Raport **botga** (shaxsiy chatga), budilnikdan keyin 30 daqiqa ichida yuboriladi:
   - **1–6 kun** — gapni o'qigan ovozli xabar;
   - **7-kundan** — tashqarida, kamera ko'chaga qaragan, gapni o'qigan **video krujok**.
     Uni rotadan 3 kishi gap bilan solishtirib tekshiradi, 2 tasi tasdiqlasa — qabul.
4. Raport rota guruhiga avtomatik e'lon qilinadi. Tonggi oyna yopilganda guruhga **TONGGI RAPORT** chiqadi:
   kim safda, kim turib raport bermadi, kim umuman yo'q.

**Jazo.** Bajarmaslik — ogohlantirish (rota guruhiga ham e'lon qilinadi). 3 ta — lagerdan chiqariladi va guruhdan haydaladi.

## Konsepsiya → kod

| Konsepsiya | Qayerda |
|---|---|
| Jins birinchi so'raladi, keyin o'zgarmaydi | `services.register_user` |
| Ariza va admin tasdig'i (Telegram'da) | `bot/handlers/onboarding.py`, `bot/handlers/admin.py`, `services.approve_user` |
| 7 kishilik rota | `rules.SQUAD_SIZE`, `services.assign_squad` |
| Manifest + do'st taklifi → 1 Joker | `accounts/manifest.py`; Joker do'st **tasdiqlanganda** beriladi |
| Gender-izolyatsiya | Qabila `(oqim, jins, vaqt)`; rota guruhiga kirish faqat so'rov orqali, bot tekshiradi |
| Kaizen −5 daqiqa | `rules.alarm_time_for_day` |
| Uyg'ondim → gap → raport | `services.press_wake`, `record_voice`, `proofs.submit_video` |
| 3 tadan 2 tasi tasdiqlasa | `proofs.services.cast_vote`, `rules.approval_threshold` |
| Oynalar 05:30–07:30, 20:30–21:30 | `Cohort` maydonlari; bot rota chatini qulflaydi/ochadi |
| Tonggi raport | `services.squad_report`, `bot/tasks.py` |
| 3 Strike = Out, Joker strike'ni o'chiradi | `services.issue_strike` |
| Yakshanba: strike yo'q, bajarsa Joker | `services.evaluate_day` |
| Muzlatish: 1 marta, faqat kechqurun ertangi kun uchun | `services.request_freeze` |
| Bosqichlar 3/7/21/40 | `rules.STAGES` |

### Tasdiqlash kerak bo'lgan qarorlar

Konsepsiyada aniq bo'lmagan joylarda quyidagicha qaror qilindi — hammasi `backend/apps/camp/rules.py` da bitta qatorda o'zgaradi:

- **Video va −5 daqiqa 7-kundan** boshlanadi (1–6 kunlar: ovozli raport).
- **"Vaqtida turish"** — budilnikdan keyin 5 daqiqa ichida «Uyg'ondim»; **raport** — 30 daqiqa ichida.
- **Joker** keyingi strike'da avtomatik ishlatiladi ("tasodifiy" emas).
- **Kun oxirigacha ovoz berilmagan video** — tasdiqlangan deb hisoblanadi.
- **Muzlatish** 18:00 dan keyin bosiladi.
- **Referral Joker** do'st havola orqali kelib, admin tasdiqlaganda beriladi.

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

**Rota guruhini ulash:** Telegram'da yopiq guruh oching → botni qo'shib **admin** qiling → guruhda `/ulash` →
rotani tanlang. Bot kirish havolasini yaratadi, rota a'zolariga yuboradi va guruhga faqat shu rota a'zolarini kiritadi.

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

Kunlik jarayon — har kuni ~00:05 da cron/Task Scheduler orqali:

```bash
cd backend && ../venv/Scripts/python manage.py run_daily
```

Testlar:

```bash
cd backend && ../venv/Scripts/python manage.py test apps
```
