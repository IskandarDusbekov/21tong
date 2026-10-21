import secrets

from django.contrib.auth.models import AbstractUser
from django.db import models


def generate_referral_code():
    return secrets.token_urlsafe(6)


class Gender(models.TextChoices):
    MALE = "M", "Yigit"
    FEMALE = "F", "Qiz"


class Region(models.TextChoices):
    TASHKENT_CITY = "tashkent_city", "Toshkent shahri"
    TASHKENT = "tashkent", "Toshkent viloyati"
    ANDIJAN = "andijan", "Andijon"
    BUKHARA = "bukhara", "Buxoro"
    FERGANA = "fergana", "Farg'ona"
    JIZZAKH = "jizzakh", "Jizzax"
    KHOREZM = "khorezm", "Xorazm"
    NAMANGAN = "namangan", "Namangan"
    NAVOI = "navoi", "Navoiy"
    KASHKADARYA = "kashkadarya", "Qashqadaryo"
    KARAKALPAKSTAN = "karakalpakstan", "Qoraqalpog'iston"
    SAMARKAND = "samarkand", "Samarqand"
    SIRDARYA = "sirdarya", "Sirdaryo"
    SURKHANDARYA = "surkhandarya", "Surxondaryo"
    ABROAD = "abroad", "Xorijda"


class User(AbstractUser):
    """
    Platforma foydalanuvchisi. Telegram orqali keladi, shuning uchun parol shart emas.

    `gender` — butun tizim shu maydon asosida ikki parallel olamga ajraladi
    (rotalar, P2P tekshiruv, lenta). Ro'yxatdan o'tgandan keyin o'zgartirilmaydi.
    """

    class Status(models.TextChoices):
        NEW = "new", "Yangi (ariza to'ldirilmoqda)"
        PENDING = "pending", "Ariza ko'rib chiqilmoqda"
        APPROVED = "approved", "Qabul qilingan"
        REJECTED = "rejected", "Rad etilgan"

    telegram_id = models.BigIntegerField("Telegram ID", unique=True, null=True, blank=True)
    telegram_username = models.CharField("Telegram username", max_length=64, blank=True)
    # Telegram'ning o'z ma'lumotlari (foydalanuvchi kiritgan ism-familiyadan alohida)
    telegram_first_name = models.CharField("Telegram ismi", max_length=128, blank=True)
    telegram_last_name = models.CharField("Telegram familiyasi", max_length=128, blank=True)
    telegram_language = models.CharField("Til kodi", max_length=8, blank=True)
    telegram_is_premium = models.BooleanField("Telegram Premium", default=False)
    gender = models.CharField("Jins", max_length=1, choices=Gender.choices, blank=True)
    region = models.CharField("Viloyat", max_length=20, choices=Region.choices, blank=True)
    goal = models.TextField("Maqsad", blank=True)
    # Arizada tanlangan tayyor rota vaqti — tasdiqlanganda shu vaqt bilan rotaga joylashtiriladi
    preferred_slot = models.ForeignKey(
        "camp.WakeSlot", null=True, blank=True, on_delete=models.SET_NULL, related_name="applicants",
        verbose_name="Tanlagan rota vaqti",
    )
    current_wake_time = models.TimeField("Hozir turadigan vaqti", null=True, blank=True)
    target_wake_time = models.TimeField("Maqsad qilgan vaqti", null=True, blank=True)
    status = models.CharField("Ariza holati", max_length=16, choices=Status.choices, default=Status.NEW)

    referral_code = models.CharField("Taklif kodi", max_length=16, unique=True, default=generate_referral_code)
    referred_by = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="referrals", verbose_name="Taklif qilgan"
    )
    # Manifestni ulashib, do'st taklif qilgani uchun berilgan Immunitet (bir marta)
    referral_immunity_granted = models.BooleanField("Taklif uchun Immunitet olgan", default=False)

    approved_at = models.DateTimeField("Qabul qilingan vaqt", null=True, blank=True)

    class Meta(AbstractUser.Meta):
        verbose_name = "Foydalanuvchi"
        verbose_name_plural = "Foydalanuvchilar"

    def __str__(self):
        if self.telegram_username:
            return f"@{self.telegram_username}"
        return self.get_full_name() or self.username

    @property
    def display_name(self):
        return self.get_full_name() or self.first_name or self.telegram_username or self.username

    @property
    def telegram_link(self):
        """Admin to'g'ridan-to'g'ri yozishi uchun havola."""
        if self.telegram_username:
            return f"https://t.me/{self.telegram_username}"
        if self.telegram_id:
            return f"tg://user?id={self.telegram_id}"
        return ""

    @property
    def telegram_full_name(self):
        return " ".join(p for p in (self.telegram_first_name, self.telegram_last_name) if p)
