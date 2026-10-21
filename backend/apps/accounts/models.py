import secrets

from django.contrib.auth.models import AbstractUser
from django.db import models


def generate_referral_code():
    return secrets.token_urlsafe(6)


class Gender(models.TextChoices):
    MALE = "M", "Yigit"
    FEMALE = "F", "Qiz"


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
    gender = models.CharField("Jins", max_length=1, choices=Gender.choices, blank=True)
    goal = models.TextField("Maqsad", blank=True)
    # Arizada ko'rsatilgan vaqtlar — tasdiqlanganda oqimga shu vaqtlar bilan joylashtiriladi
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
