"""
Ikki xil mijoz:
  * Bot      — `X-Bot-Secret` sarlavhasi (server-server).
  * Mini App — `Authorization: tma <initData>` (Telegram imzosi HMAC orqali tekshiriladi).
"""
import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from django.conf import settings
from rest_framework import authentication, exceptions, permissions

from .models import User


def validate_init_data(init_data: str, bot_token: str, max_age: int):
    """Telegram Web App initData imzosini tekshiradi va `user` lug'atini qaytaradi."""
    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise ValueError("hash yo'q")
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received_hash):
        raise ValueError("imzo noto'g'ri")
    auth_date = int(pairs.get("auth_date", "0"))
    if max_age and time.time() - auth_date > max_age:
        raise ValueError("initData eskirgan")
    return json.loads(pairs.get("user", "{}"))


class TelegramInitDataAuthentication(authentication.BaseAuthentication):
    keyword = "tma"

    def authenticate(self, request):
        header = request.headers.get("Authorization", "")
        if not header.startswith(self.keyword + " "):
            return None
        try:
            tg_user = validate_init_data(
                header[len(self.keyword) + 1:], settings.TELEGRAM_BOT_TOKEN, settings.TMA_INIT_DATA_MAX_AGE
            )
        except (ValueError, json.JSONDecodeError) as exc:
            raise exceptions.AuthenticationFailed(f"initData: {exc}")
        user = User.objects.filter(telegram_id=tg_user.get("id")).first()
        if user is None:
            raise exceptions.AuthenticationFailed("Avval botda ro'yxatdan o'ting.")
        return user, None

    def authenticate_header(self, request):
        return self.keyword


class DevAuthentication(authentication.BaseAuthentication):
    """
    Faqat lokal ishlab chiqish uchun: `Authorization: dev <telegram_id>`.
    Mini App'ni Telegram'siz, oddiy brauzerda ko'rish imkonini beradi.
    DEV_LOGIN o'chiq bo'lsa (production'da DEBUG=false) umuman ishlamaydi.
    """

    keyword = "dev"

    def authenticate(self, request):
        if not settings.DEV_LOGIN:
            return None
        header = request.headers.get("Authorization", "")
        if not header.startswith(self.keyword + " "):
            return None
        user = User.objects.filter(telegram_id=header[len(self.keyword) + 1:].strip() or None).first()
        if user is None:
            raise exceptions.AuthenticationFailed("Dev: bunday telegram_id li foydalanuvchi yo'q.")
        return user, None


class IsBot(permissions.BasePermission):
    def has_permission(self, request, view):
        secret = request.headers.get("X-Bot-Secret", "")
        return bool(settings.BOT_API_SECRET) and hmac.compare_digest(secret, settings.BOT_API_SECRET)
