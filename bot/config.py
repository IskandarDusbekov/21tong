import os
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
BOT_API_SECRET = os.getenv("BOT_API_SECRET", "dev-bot-secret")
MINI_APP_URL = os.getenv("MINI_APP_URL", "")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0") or 0)
TZ = ZoneInfo(os.getenv("TIME_ZONE", "Asia/Tashkent"))
