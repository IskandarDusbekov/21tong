# 21tong

Odamlarning uyqu va hayot rejimini to'g'rilovchi, qat'iy intizomga asoslangan 21 kunlik onlayn lager.
Telegram Bot + Telegram Mini App (React) + Django/PostgreSQL.

## Tuzilma

```
backend/            Django + DRF — barcha biznes-qoidalar shu yerda
  apps/accounts/    User (telegram_id, jins, maqsad, admin tasdig'i, referral), Manifest rasmi, auth
  apps/camp/        Oqim, Qabila, Ishtirok, Kunlik yozuv, Strike, Joker, Muzlatish, Notification outbox
    rules.py        Lager raqamlari va sof funksiyalar (Kaizen, bosqichlar, kvorum...)
    services.py     Holatni o'zgartiruvchi yagona joy (bot ham, Mini App ham shu orqali)
  apps/proofs/      Video isbot va P2P tekshiruv (faqat bir jinsdagilar)
  apps/community/   Kechki refleksiya, 🔥, Bounty, IrodaCoin
  apps/api/         /api/bot/* (X-Bot-Secret) va /api/app/* (Telegram initData)
bot/                aiogram 3 — onboarding, voice/video qabul qilish, ovoz berish, budilnik, chat oynalari
miniapp/            React + Vite — Bugun / Lenta / Bounty / Reyting
```

Bot hech qanday qoidani o'zi hal qilmaydi: u backend'ga so'rov yuboradi va `Notification` navbatidagi
voqealarni (strike, joker, tekshiruv so'rovi...) Serjant/Murabbiy ohangida yetkazadi (`bot/texts.py`).

## Konsepsiya → kod

| Konsepsiya | Qayerda |
|---|---|
| Jins birinchi so'raladi, keyin o'zgarmaydi | `services.register_user` |
| Admin tasdig'i | Django admin → Users → "Tasdiqlash" action |
| Manifest + do'st taklifi → 1 Joker | `accounts/manifest.py`; Joker do'st **tasdiqlanganda** beriladi (`approve_user`) |
| Gender-izolyatsiya | Qabila `(oqim, jins, vaqt)` bo'yicha; tekshiruvchi, lenta, 🔥, reyting — faqat o'z jinsi |
| Kaizen −5 daqiqa | `rules.alarm_time_for_day` |
| 3 qadamli zanjir | Mini App «Uyg'ondim» → guruhda voice → botga video krujok |
| 3 tadan 2 tasi tasdiqlasa | `proofs.services.cast_vote`, `rules.approval_threshold` |
| Oynalar 05:30–07:30, 20:30–21:30 | `Cohort` maydonlari; bot chatni qulflaydi/ochadi |
| 3 Strike = Out, Joker strike'ni o'chiradi | `services.issue_strike` |
| Yakshanba: strike yo'q, bajarsa Joker | `services.evaluate_day` |
| Muzlatish: 1 marta, faqat kechqurun ertangi kun uchun | `services.request_freeze` |
| Bosqichlar 3/7/21/40 | `rules.STAGES` |

### Tasdiqlash kerak bo'lgan qarorlar

Konsepsiyada aniq bo'lmagan joylarda quyidagicha qaror qilindi — hammasi `backend/apps/camp/rules.py` da bitta qatorda o'zgaradi:

- **Video va −5 daqiqa 7-kundan** boshlanadi (1–6 kunlar: faqat vaqtida turish + voice).
- **"Vaqtida turish"** — budilnikdan keyin 5 daqiqa ichida «Uyg'ondim» bosilishi.
- **Joker** keyingi strike'da avtomatik ishlatiladi ("tasodifiy" emas).
- **Kun oxirigacha ovoz berilmagan video** — tasdiqlangan deb hisoblanadi (dangasa tekshiruvchi uchun ishtirokchi jazolanmaydi).
- **Muzlatish** 18:00 dan keyin bosiladi.
- **Referral Joker** storis tekshirib bo'lmagani uchun do'st havola orqali kelib, admin tasdiqlaganda beriladi.

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

Bot (`.env` da `TELEGRAM_BOT_TOKEN` kerak):

```bash
cd bot && ../venv/Scripts/python main.py
```

Mini App (`/api` so'rovlari Django'ga proxy qilinadi):

```bash
cd miniapp && npm install && npm run dev
```

Kunlik jarayon — har kuni ~00:05 da cron/Task Scheduler orqali:

```bash
cd backend && ../venv/Scripts/python manage.py run_daily
```

Testlar:

```bash
cd backend && ../venv/Scripts/python manage.py test apps
```

## Telegram sozlamalari

1. BotFather'da bot yarating, Mini App URL'ini (HTTPS) ulang.
2. Har bir qabila uchun yopiq guruh oching, botni **admin** qiling (xabar yuborish huquqini boshqarish uchun).
3. Admin panelda Oqim yarating; qabilalarga guruh `telegram_chat_id` va `invite_link` ni kiriting.
