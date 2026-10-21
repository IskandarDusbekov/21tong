"""
Boshqaruv: lagerning kod yozmasdan o'zgartiriladigan barcha sozlamalari.
  * CampSettings — vaqtlar, muddatlar, jazo, rota hajmi (yagona yozuv)
  * Phrase       — uyg'ongach o'qiladigan gaplar
  * Stage        — bosqichlar (3/7/21/40-kun)
  * BotMessage   — botning har bir xabar matni
  * Broadcast    — ommaviy xabar
"""
import datetime as dt
import string

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.accounts.models import Gender

from . import defaults

CACHE_KEY = "camp_settings"


def minutes(default, low=0, high=600, **kw):
    return models.PositiveSmallIntegerField(
        default=default, validators=[MinValueValidator(low), MaxValueValidator(high)], **kw
    )


class CampSettings(models.Model):
    """Lager qoidalari. Faqat bitta yozuv bo'ladi — admin panelda "Lager sozlamalari"."""

    # --- Uyg'onish va raport ---
    wake_grace_minutes = minutes(5, 1, 60, verbose_name="«Uyg'ondim» uchun vaqt (daqiqa)",
                                 help_text="Budilnikdan keyin shuncha daqiqa ichida «Uyg'ondim» bosilmasa — kech turdi.")
    voice_deadline_minutes = minutes(5, 1, 120, verbose_name="Ovozli raport muddati (daqiqa)",
                                     help_text="Budilnikdan keyin shuncha daqiqa ichida ovozli raport yuborilishi shart.")
    video_from_day = minutes(0, 0, 365, verbose_name="Video raport nechanchi kundan",
                             help_text="0 — video umuman so'ralmaydi, har kuni ovozli raport. Masalan 7 — 7-kundan video krujok.")
    video_deadline_minutes = minutes(20, 1, 180, verbose_name="Video raport muddati (daqiqa)",
                                     help_text="Video talab qilinadigan kunlarda budilnikdan keyingi muddat.")
    reviewers_per_proof = minutes(3, 1, 10, verbose_name="Videoni nechta rotadosh tekshiradi",
                                  help_text="Ko'pchilik (masalan 3 dan 2) tasdiqlasa — qabul.")
    unreviewed_counts_as_approved = models.BooleanField(
        "Tekshirilmagan video tasdiqlangan hisoblansin", default=True,
        help_text="Kun oxirigacha hech kim ovoz bermagan video uchun ishtirokchi jazolanmaydi.",
    )

    # --- Kaizen ---
    shift_from_day = minutes(3, 1, 365, verbose_name="Budilnik surilishi nechanchi kundan")
    shift_step_minutes = minutes(5, 1, 60, verbose_name="Har kuni necha daqiqaga suriladi")

    # --- Jazo va mukofot ---
    max_strikes = minutes(3, 1, 20, verbose_name="Nechta ogohlantirishda chiqariladi")
    sunday_rest = models.BooleanField("Yakshanba — dam olish kuni", default=True,
                                      help_text="Yakshanba bajarmaganlarga ogohlantirish berilmaydi.")
    sunday_immunity = models.BooleanField("Yakshanba bajarganlarga Immunitet", default=True)
    referral_immunity = models.BooleanField("Do'st taklifi uchun Immunitet", default=False,
                                            help_text="Yoqilsa: havola orqali kelgan do'st qabul qilinganda taklif qilganga bir marta. "
                                                      "Standart o'chiq — aks holda Immunitetlar ko'payib ketadi.")
    freezes_per_cohort = minutes(1, 0, 10, verbose_name="Oqimda nechta muzlatish (kasallik)")
    freeze_allowed_from = models.TimeField("Muzlatishni qaysi vaqtdan bosish mumkin", default=dt.time(18, 0),
                                           help_text="Faqat shu vaqtdan keyin, ertangi kun uchun.")

    # --- Jamoa ---
    squad_size = minutes(7, 2, 50, verbose_name="Rotada necha kishi")
    reflection_max_length = minutes(200, 20, 1000, verbose_name="Refleksiya uzunligi (belgi)")
    registration_open = models.BooleanField("Ariza qabul qilinadi", default=True,
                                            help_text="O'chirilsa, bot yangi ariza qabul qilmaydi.")

    # --- Yangi oqim uchun standart qiymatlar ---
    default_duration_days = minutes(21, 1, 365, verbose_name="Oqim davomiyligi (kun)")
    default_morning_start = models.TimeField("Tonggi oyna boshlanishi", default=dt.time(5, 30))
    default_morning_end = models.TimeField("Tonggi oyna tugashi", default=dt.time(7, 30))
    default_evening_start = models.TimeField("Kechki oyna boshlanishi", default=dt.time(20, 30))
    default_evening_end = models.TimeField("Kechki oyna tugashi", default=dt.time(21, 30))

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Lager sozlamalari"
        verbose_name_plural = "Lager sozlamalari"

    def __str__(self):
        return "Lager sozlamalari"

    def clean(self):
        if self.default_morning_start >= self.default_morning_end:
            raise ValidationError("Tonggi oyna boshlanishi tugashidan oldin bo'lishi kerak.")
        if self.default_evening_start >= self.default_evening_end:
            raise ValidationError("Kechki oyna boshlanishi tugashidan oldin bo'lishi kerak.")

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
        cache.delete(CACHE_KEY)

    def delete(self, *args, **kwargs):
        pass  # yagona yozuv o'chirilmaydi

    @classmethod
    def load(cls):
        obj = cache.get(CACHE_KEY)
        if obj is None:
            obj, _ = cls.objects.get_or_create(pk=1)
            cache.set(CACHE_KEY, obj, 30)
        return obj

    def template_vars(self):
        """Bot matnlarida ishlatiladigan sozlama o'zgaruvchilari."""
        return {
            "wake_grace": self.wake_grace_minutes,
            "voice_deadline": self.voice_deadline_minutes,
            "video_deadline": self.video_deadline_minutes,
            "shift_from_day": self.shift_from_day,
            "shift_step": self.shift_step_minutes,
            "video_from_day": self.video_from_day,
            "max_strikes": self.max_strikes,
            "squad_size": self.squad_size,
            "reviewers": self.reviewers_per_proof,
            "freeze_from": self.freeze_allowed_from.strftime("%H:%M"),
            "duration": self.default_duration_days,
        }


# Sozlamalar sahifasidagi guruhlar: (sarlavha, ikonka, maydonlar). Admin va boshqaruv paneli ishlatadi.
SETTINGS_GROUPS = [
    ("Uyg'onish va raport", "alarm-clock", [
        "wake_grace_minutes", "voice_deadline_minutes", "video_from_day", "video_deadline_minutes",
        "reviewers_per_proof", "unreviewed_counts_as_approved",
    ]),
    ("Kaizen — budilnikni surish", "trending-down", ["shift_from_day", "shift_step_minutes"]),
    ("Jazo va mukofot", "shield", [
        "max_strikes", "sunday_rest", "sunday_immunity", "referral_immunity",
        "freezes_per_cohort", "freeze_allowed_from",
    ]),
    ("Jamoa va ariza", "users", ["squad_size", "reflection_max_length", "registration_open"]),
    ("Yangi oqim uchun standart qiymatlar", "calendar", [
        "default_duration_days", "default_morning_start", "default_morning_end",
        "default_evening_start", "default_evening_end",
    ]),
]


class Phrase(models.Model):
    text = models.CharField("Gap", max_length=200)
    is_active = models.BooleanField("Faol", default=True)

    class Meta:
        verbose_name = "O'qiladigan gap"
        verbose_name_plural = "O'qiladigan gaplar"
        ordering = ["id"]

    def __str__(self):
        return self.text


class Stage(models.Model):
    class Icon(models.TextChoices):
        SPROUT = "sprout", "Nihol"
        MOUNTAIN = "mountain", "Tog'"
        SHIELD = "shield", "Qalqon"
        CROWN = "crown", "Toj"
        FLAME = "flame", "Olov"
        STAR = "star", "Yulduz"
        MEDAL = "medal", "Medal"

    class AwardType(models.TextChoices):
        PAGON = "pagon", "Pogon (harbiy unvon)"
        MEDAL = "medal", "Medal"
        CERTIFICATE = "certificate", "Sertifikat"

    day = models.PositiveSmallIntegerField("Nechanchi kundan keyin", unique=True)
    name = models.CharField("Nomi", max_length=60)
    description = models.CharField("Tavsif", max_length=250, blank=True)
    icon = models.CharField("Ikonka", max_length=16, choices=Icon.choices, default=Icon.STAR)
    award_type = models.CharField("Mukofot turi", max_length=16, choices=AwardType.choices, default=AwardType.MEDAL)
    rank = models.CharField("Harbiy unvon", max_length=40, blank=True, help_text="Masalan: «Kichik serjant». Pogon va sertifikatda yoziladi.")
    stars = models.PositiveSmallIntegerField("Pogondagi yulduzlar", default=1, validators=[MaxValueValidator(4)])

    class Meta:
        verbose_name = "Bosqich"
        verbose_name_plural = "Bosqichlar"
        ordering = ["day"]

    def __str__(self):
        return f"{self.day}-kun · {self.name}"


class _SafeVars(dict):
    def __missing__(self, key):
        return "{" + key + "}"


class BotMessage(models.Model):
    """Botning bitta xabari. Kalit kodda ishlatiladi, matnni admin o'zgartiradi."""

    key = models.CharField("Kalit", max_length=40, unique=True, editable=False)
    group = models.CharField("Bo'lim", max_length=20, editable=False)
    title = models.CharField("Qayerda ishlatiladi", max_length=100, editable=False)
    text = models.TextField("Matn")
    # Admin o'zgartirmagan xabarlar dastur yangilanganda yangi standart matnga o'tadi
    customized = models.BooleanField("Admin o'zgartirgan", default=False, editable=False)
    updated_at = models.DateTimeField("O'zgartirilgan", auto_now=True)

    class Meta:
        verbose_name = "Bot xabari"
        verbose_name_plural = "Bot xabarlari"
        ordering = ["group", "key"]

    def __str__(self):
        return self.title

    @property
    def variables(self):
        own = defaults.MESSAGES.get(self.key, (None, None, ()))[2]
        return tuple(own) + defaults.SETTINGS_VARS

    @property
    def default_text(self):
        return defaults.MESSAGES.get(self.key, (None, None, None, ""))[3]

    def clean(self):
        allowed = set(self.variables)
        try:
            fields = [f for _, f, _, _ in string.Formatter().parse(self.text) if f is not None]
        except ValueError:
            raise ValidationError({"text": "Figurali qavslar { } juftligi buzilgan."})
        unknown = sorted({f for f in fields if f and f not in allowed})
        if unknown:
            raise ValidationError({"text": f"Noma'lum o'zgaruvchi: {', '.join('{' + u + '}' for u in unknown)}"})

    def render(self, **values):
        return self.text.format_map(_SafeVars(values))

    def save(self, *args, **kwargs):
        self.customized = self.text != self.default_text
        super().save(*args, **kwargs)

    @classmethod
    def sync_defaults(cls):
        """
        Yangi kalitlarni qo'shadi, eskirganlarini o'chiradi. Admin o'zgartirmagan matnlar yangi standartga
        o'tadi; admin o'zgartirganlariga tegilmaydi.
        """
        existing = set(cls.objects.values_list("key", flat=True))
        cls.objects.bulk_create([
            cls(key=k, group=g, title=t, text=txt)
            for k, (g, t, _, txt) in defaults.MESSAGES.items() if k not in existing
        ])
        cls.objects.exclude(key__in=defaults.MESSAGES.keys()).delete()
        for k, (g, t, _, txt) in defaults.MESSAGES.items():
            cls.objects.filter(key=k).exclude(group=g, title=t).update(group=g, title=t)
            cls.objects.filter(key=k, customized=False).exclude(text=txt).update(text=txt)


class Broadcast(models.Model):
    """Ommaviy xabar: saqlanganda tanlangan auditoriyaga bot orqali yuboriladi."""

    class Audience(models.TextChoices):
        ACTIVE = "active", "Barcha faol ishtirokchilar"
        APPROVED = "approved", "Barcha qabul qilinganlar"
        PENDING = "pending", "Arizasi ko'rib chiqilayotganlar"
        COHORT = "cohort", "Tanlangan oqim"
        SQUAD = "squad", "Tanlangan rota"

    text = models.TextField("Xabar matni", help_text="HTML: <b>qalin</b>, <i>kursiv</i>.")
    audience = models.CharField("Kimga", max_length=16, choices=Audience.choices, default=Audience.ACTIVE)
    cohort = models.ForeignKey("camp.Cohort", null=True, blank=True, on_delete=models.SET_NULL, verbose_name="Oqim")
    squad = models.ForeignKey("camp.Squad", null=True, blank=True, on_delete=models.SET_NULL, verbose_name="Rota")
    gender = models.CharField("Jins", max_length=1, choices=Gender.choices, blank=True,
                              help_text="Bo'sh — hammaga.")
    created_at = models.DateTimeField("Yaratilgan", auto_now_add=True)
    sent_count = models.PositiveIntegerField("Yuborildi (kishi)", default=0, editable=False)

    class Meta:
        verbose_name = "Ommaviy xabar"
        verbose_name_plural = "Ommaviy xabarlar"
        ordering = ["-created_at"]

    def __str__(self):
        return self.text[:60]

    def clean(self):
        if self.audience == self.Audience.COHORT and not self.cohort:
            raise ValidationError({"cohort": "Oqimni tanlang."})
        if self.audience == self.Audience.SQUAD and not self.squad:
            raise ValidationError({"squad": "Rotani tanlang."})
