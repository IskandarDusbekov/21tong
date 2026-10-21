import os
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
BOT_API_SECRET = os.getenv("BOT_API_SECRET", "dev-bot-secret")
MINI_APP_URL = os.getenv("MINI_APP_URL", "")
# Arizalarni tasdiqlaydigan adminlar (Telegram ID, vergul bilan). ID'ni @userinfobot dan bilish mumkin.
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x}
TZ = ZoneInfo(os.getenv("TIME_ZONE", "Asia/Tashkent"))


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS
