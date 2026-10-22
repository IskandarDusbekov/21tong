# 21tong — serverga joylash

Ikki bosqich:

- **1–7-qadamlar** (pastda): bot + backend ni IP bilan ishga tushirish — arizalarni darhol qabul
  qilish uchun yetarli. Adminlar arizani **Telegram'dagi ✅/❌ tugmalari** bilan tasdiqlaydi.
- **«Domen + SSL + Mini App»** (eng oxirda): domen ulab, Mini App, panel va admin'ni HTTPS orqali
  to'liq ishga tushirish.

Agar domeningiz tayyor bo'lsa — avval 1–7 ni, keyin oxirgi bo'limni bajaring.

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

## Domen + SSL + Mini App (to'liq ishga tushirish)

Domen (masalan `21tong.uz`) serverning IP'siga **A-yozuv** bilan ulangan bo'lsin (DNS). Bu bo'lim
botni, Mini App'ni, panel va admin'ni bitta domenda HTTPS orqali ochadi. Quyida `21tong.uz` o'rniga
o'z domeningizni, `/home/ubuntu` o'rniga o'z yo'lingizni qo'ying.

### 1. Frontend'larni build qilish (Node.js kerak)

```bash
sudo apt install -y nodejs npm
cd ~/21tong/miniapp && npm ci && npm run build
cd ~/21tong/panel   && npm ci && npm run build
```

### 2. Django static fayllarini yig'ish

```bash
cd ~/21tong/backend && ../venv/bin/python manage.py collectstatic --noinput
```

### 3. `.env` ni production'ga moslash

```
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost,21tong.uz,www.21tong.uz
DJANGO_CSRF_TRUSTED_ORIGINS=https://21tong.uz,https://www.21tong.uz
MINI_APP_URL=https://21tong.uz
```

> `MINI_APP_URL` o'rnatilgach bot doimiy «Menu» tugmasini avtomatik Mini App'ga bog'laydi —
> BotFather'da qo'lda sozlash shart emas.

### 4. nginx o'rnatish va config

```bash
sudo apt install -y nginx
sudo cp ~/21tong/deploy/nginx-21tong.conf /etc/nginx/sites-available/21tong
sudo sed -i 's/SIZNING_DOMEN/21tong.uz/g' /etc/nginx/sites-available/21tong   # domeningizni qo'ying
sudo ln -sf /etc/nginx/sites-available/21tong /etc/nginx/sites-enabled/21tong
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

> `nginx-21tong.conf` ichidagi `/home/ubuntu` yo'li boshqa bo'lsa — faylni ochib to'g'rilang.

### 5. SSL sertifikat (Let's Encrypt — bepul, avtomatik)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d 21tong.uz -d www.21tong.uz
```

Certbot HTTPS (443) blokini va HTTP→HTTPS yo'naltirishni **o'zi qo'shadi**; sertifikat avtomatik
yangilanadi (`sudo certbot renew --dry-run` bilan tekshiring).

### 6. Backend va botni qayta ishga tushirish

```bash
sudo systemctl restart 21tong-backend 21tong-bot
```

### 7. Tekshirish

- `https://21tong.uz/` — Mini App ochiladi (brauzerda "Dev kirish" `DEBUG=false` da o'chiq bo'ladi —
  bu normal; Mini App faqat Telegram ichida to'liq ishlaydi).
- `https://21tong.uz/panel/` — boshqaruv paneli (admin login bilan).
- `https://21tong.uz/admin/` — Django admin.
- Telegram'da botning pastidagi **«Menu»** tugmasi Mini App'ni ochadi.

### Kodni yangilaganda (domen bilan)

```bash
cd ~/21tong && git pull
./venv/bin/pip install -r backend/requirements.txt -r bot/requirements.txt
cd backend && ../venv/bin/python manage.py migrate && ../venv/bin/python manage.py collectstatic --noinput
cd ../miniapp && npm ci && npm run build
cd ../panel   && npm ci && npm run build
sudo systemctl restart 21tong-backend 21tong-bot
```
