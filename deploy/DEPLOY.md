# 21tong — serverga joylash (hozircha IP bilan, arizalar uchun)

Maqsad: **bot + backend** ni serverda ishga tushirish, arizalarni oldindan qabul qila boshlash.
Adminlar arizani **Telegram'dagi ✅/❌ tugmalari** bilan tasdiqlaydi — veb-panel hozircha shart emas.
Mini App (HTTPS kerak), domen, SSL, nginx va Docker — **ertaga** (pastda eslatma bor).

Quyidagilar **serverda** (SSH orqali) bajariladi. `ubuntu` va yo'llarni o'zingiznikiga moslang.

## 1. Tayyorgarlik (Ubuntu/Debian)

```bash
sudo apt update && sudo apt install -y python3 python3-venv python3-pip git
```

## 2. Kodni serverga olish

Git bilan:

```bash
cd ~ && git clone <SIZNING_REPO_URL> 21tong && cd 21tong
```

Yoki kompyuteringizdan yuklab (git yo'q bo'lsa), lokal mashinada:

```bash
scp -r C:/Users/user/Desktop/21tong ubuntu@SERVER_IP:/home/ubuntu/21tong
```

> `venv/`, `db.sqlite3`, `__pycache__`, `node_modules` ni yubormang — ular serverda qayta yaratiladi.

## 3. Virtual muhit va kutubxonalar

```bash
cd ~/21tong && python3 -m venv venv
./venv/bin/pip install -r backend/requirements.txt -r bot/requirements.txt
```

## 4. `.env` faylini to'ldirish

```bash
cp .env.example .env && nano .env
```

Ishga tushirish uchun muhim qiymatlar:

```
DJANGO_SECRET_KEY=<uzun tasodifiy satr>
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost,SERVER_IP
TIME_ZONE=Asia/Tashkent

# Postgres'ni bo'sh qoldirsangiz — SQLite ishlaydi (boshlash uchun yetarli)
POSTGRES_DB=

TELEGRAM_BOT_TOKEN=<BotFather token>
TELEGRAM_BOT_USERNAME=<bot_username>
BOT_API_SECRET=<uzun tasodifiy satr>
BACKEND_URL=http://127.0.0.1:8000
ADMIN_IDS=<sizning_telegram_id>        # bir nechta bo'lsa vergul bilan
MINI_APP_URL=                           # hozircha bo'sh (HTTPS kelgach to'ldiriladi)
```

Tasodifiy kalit yaratish:

```bash
./venv/bin/python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## 5. Ma'lumotlar bazasi va admin

```bash
cd ~/21tong/backend
../venv/bin/python manage.py migrate
../venv/bin/python manage.py createsuperuser
```

## 6. Doimiy ishlashi uchun (systemd)

`deploy/` dagi ikki xizmat faylidagi `User` va yo'llarni tekshiring, keyin:

```bash
sudo cp ~/21tong/deploy/21tong-backend.service ~/21tong/deploy/21tong-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now 21tong-backend 21tong-bot
```

Holatini ko'rish:

```bash
systemctl status 21tong-backend 21tong-bot --no-pager
```

## 7. Tekshirish

- `journalctl -u 21tong-bot -f` — "Bot ishga tushdi: @..." chiqishi kerak.
- Telegram'da botga `/start` yozing — ariza boshlanadi.
- Arizani yuboring — u `ADMIN_IDS` dagi adminlarga **✅ Qabul / ❌ Rad** tugmalari bilan keladi.
- Qabul qilsangiz — foydalanuvchiga rota, start sanasi va yo'riqnoma keladi.

> Kunlik hisob (kechagi kunni baholash, oqimni boshlash) uchun **cron shart emas** — bot buni har kecha
> 00:05 da va har ishga tushganda o'zi bajaradi.

## Kundalik buyruqlar

```bash
# Loglar
journalctl -u 21tong-bot -f
journalctl -u 21tong-backend -f

# Qayta ishga tushirish
sudo systemctl restart 21tong-backend 21tong-bot

# Kodni yangilash
cd ~/21tong && git pull
./venv/bin/pip install -r backend/requirements.txt -r bot/requirements.txt
cd backend && ../venv/bin/python manage.py migrate
sudo systemctl restart 21tong-backend 21tong-bot
```

## Ertaga: domen + SSL + Mini App

Domen serverga ulanib, SSL (masalan Certbot) olingach:

1. nginx o'rnatib, `backend` ni `127.0.0.1:8000` dan HTTPS orqali `proxy_pass` qiling; `/static/` va
   `/media/` ni ulang (`manage.py collectstatic`).
2. Mini App'ni build qilib (`cd miniapp && npm ci && npm run build`) `https://<domen>/` da bering.
3. `.env` da `MINI_APP_URL=https://<domen>` qo'ying va BotFather → **Menu Button / Web App** ga o'sha
   manzilni yozing. Botni qayta ishga tushiring — alarm va menyuda «📱 Mini App» tugmasi paydo bo'ladi.
4. Veb-panel (`/panel/`) va `/admin/` ni ham nginx orqali bering.

> Hozircha bularsiz ham arizalar to'liq ishlaydi — adminlar Telegram tugmalari bilan tasdiqlaydi.
