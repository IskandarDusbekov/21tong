import datetime as dt

from django.conf import settings
from django.db import models

from apps.accounts.models import Gender


class Cohort(models.Model):
    """Oqim — 21 kunlik lagerning bitta to'plami."""

    class Status(models.TextChoices):
        RECRUITING = "recruiting", "Qabul ochiq"
        RUNNING = "running", "Davom etmoqda"
        FINISHED = "finished", "Yakunlangan"

    name = models.CharField(max_length=100)
    start_date = models.DateField()
    duration_days = models.PositiveSmallIntegerField(default=21)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.RECRUITING)

    # "Oyna" usuli: chatlar faqat shu oraliqlarda ochiq
    morning_window_start = models.TimeField(default=dt.time(5, 30))
    morning_window_end = models.TimeField(default=dt.time(7, 30))
    evening_window_start = models.TimeField(default=dt.time(20, 30))
    evening_window_end = models.TimeField(default=dt.time(21, 30))

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return self.name

    @property
    def end_date(self):
        return self.start_date + dt.timedelta(days=self.duration_days - 1)

    def day_number(self, date):
        """Oqimning nechanchi kuni (1 dan boshlanadi). Oqimdan tashqarida None."""
        n = (date - self.start_date).days + 1
        return n if 1 <= n <= self.duration_days else None


class Tribe(models.Model):
    """
    Qabila — bir xil boshlang'ich uyg'onish vaqtidagi, bir jinsdagi ishtirokchilar guruhi.
    Masalan: "7:00 Qabilasi (Yigitlar)". Har biri alohida Telegram guruhiga bog'lanadi.
    """

    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, related_name="tribes")
    gender = models.CharField(max_length=1, choices=Gender.choices)
    start_wake_time = models.TimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["cohort", "gender", "start_wake_time"], name="unique_tribe_per_slot"
            )
        ]
        ordering = ["start_wake_time", "gender"]

    def __str__(self):
        return f"{self.start_wake_time:%H:%M} Qabilasi ({self.get_gender_display()}lar)"


class Squad(models.Model):
    """
    Rota — qabila ichidagi 7 kishilik jamoa. Har rotaning o'z yopiq Telegram guruhi bor:
    raportlar, ogohlantirishlar va P2P tekshiruv birinchi navbatda rota ichida.
    """

    tribe = models.ForeignKey(Tribe, on_delete=models.CASCADE, related_name="squads")
    number = models.PositiveSmallIntegerField()
    telegram_chat_id = models.BigIntegerField(null=True, blank=True, unique=True)
    invite_link = models.URLField(blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["tribe", "number"], name="unique_squad_number")]
        ordering = ["tribe", "number"]

    def __str__(self):
        return f"{self.number}-rota · {self.tribe}"

    @property
    def name(self):
        return f"{self.number}-rota"


class Membership(models.Model):
    """Foydalanuvchining bitta oqimdagi ishtiroki."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Faol"
        EXPELLED = "expelled", "Haydalgan (3 strike)"
        FINISHED = "finished", "21 kunni tugatgan"
        MENTOR = "mentor", "Mentor (40 kun)"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships")
    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, related_name="memberships")
    tribe = models.ForeignKey(Tribe, on_delete=models.PROTECT, related_name="memberships")
    squad = models.ForeignKey(Squad, null=True, blank=True, on_delete=models.SET_NULL, related_name="memberships")
    target_wake_time = models.TimeField("Maqsad qilingan uyg'onish vaqti")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "cohort"], name="one_membership_per_cohort")
        ]

    def __str__(self):
        return f"{self.user} @ {self.cohort}"

    @property
    def active_strikes(self):
        return self.strikes.filter(cancelled_by_joker=False).count()


class DayRecord(models.Model):
    """Ishtirokchining bitta kundagi holati: budilnik vaqti va 3 qadamli zanjir."""

    class Status(models.TextChoices):
        PENDING = "pending", "Kutilmoqda"
        COMPLETED = "completed", "Bajarildi"
        FAILED = "failed", "Bajarilmadi"
        REST = "rest", "Yakshanba dam olish"
        FROZEN = "frozen", "Muzlatilgan"

    membership = models.ForeignKey(Membership, on_delete=models.CASCADE, related_name="days")
    date = models.DateField()
    day_number = models.PositiveSmallIntegerField()
    alarm_time = models.TimeField()

    woke_at = models.DateTimeField(null=True, blank=True)  # 1-qadam: "Uyg'ondim"
    # Uyg'ongach beriladigan, ovoz chiqarib o'qiladigan gap. Har kuni har kimga tasodifiy —
    # eski yozuvni qayta yuborib aldab bo'lmaydi, tekshiruvchilar gapni solishtiradi.
    phrase = models.CharField(max_length=200, blank=True)
    # 2-qadam, 1–6 kunlar: gap o'qilgan ovozli raport (botga)
    voice_at = models.DateTimeField(null=True, blank=True)
    voice_file_id = models.CharField(max_length=255, blank=True)
    # 2-qadam, 7-kundan: tashqarida yozilgan video krujok — proofs.VideoProof orqali

    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    evaluated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["membership", "date"], name="one_record_per_day")
        ]
        ordering = ["date"]

    def __str__(self):
        return f"{self.membership.user} — {self.day_number}-kun ({self.date})"


class Strike(models.Model):
    class Reason(models.TextChoices):
        LATE = "late", "Vaqtida turmadi"
        NO_VOICE = "no_voice", "Ovozli xabar yubormadi"
        NO_VIDEO = "no_video", "Video yubormadi"
        REJECTED = "rejected", "Jamoa tasdiqlamadi"
        ADMIN = "admin", "Admin qarori"

    membership = models.ForeignKey(Membership, on_delete=models.CASCADE, related_name="strikes")
    day = models.ForeignKey(DayRecord, null=True, blank=True, on_delete=models.SET_NULL, related_name="strikes")
    reason = models.CharField(max_length=16, choices=Reason.choices)
    cancelled_by_joker = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Strike: {self.membership.user} ({self.get_reason_display()})"


class Joker(models.Model):
    """Immunitet: kelajakdagi 1 ta Strike'ni o'chiradi. Foydalanuvchiga tegishli (oqimlar orasida saqlanadi)."""

    class Source(models.TextChoices):
        REFERRAL = "referral", "Manifest + taklif"
        SUNDAY = "sunday", "Yakshanba barvaqt turish"
        ADMIN = "admin", "Admin sovg'asi"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="jokers")
    source = models.CharField(max_length=16, choices=Source.choices)
    granted_at = models.DateTimeField(auto_now_add=True)
    used_on = models.OneToOneField(Strike, null=True, blank=True, on_delete=models.SET_NULL, related_name="joker")

    def __str__(self):
        return f"Joker ({self.get_source_display()}) — {self.user}"


class Notification(models.Model):
    """
    Bot uchun chiquvchi xabarlar navbati (outbox). Backend voqea yozadi,
    bot uni o'qib, foydalanuvchiga mos ohangda (Serjant/Murabbiy) yuboradi.
    """

    class Kind(models.TextChoices):
        NEW_APPLICATION = "new_application", "Yangi ariza (adminlarga)"
        APPROVED = "approved", "Tasdiqlandi"
        REJECTED = "rejected", "Rad etildi"
        REVIEW_REQUEST = "review_request", "Videoni tekshirish so'rovi"
        VIDEO_APPROVED = "video_approved", "Video tasdiqlandi"
        VIDEO_REJECTED = "video_rejected", "Video rad etildi"
        STRIKE = "strike", "Strike"
        JOKER_USED = "joker_used", "Joker ishlatildi"
        JOKER_GRANTED = "joker_granted", "Joker berildi"
        EXPELLED = "expelled", "Haydaldi"
        STAGE_UP = "stage_up", "Yangi bosqich"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    kind = models.CharField(max_length=32, choices=Kind.choices)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["sent_at", "created_at"])]


class Freeze(models.Model):
    """Fors-major: butun oqimda 1 marta, faqat kechqurun ertangi kun uchun bosiladi."""

    membership = models.OneToOneField(Membership, on_delete=models.CASCADE, related_name="freeze")
    date = models.DateField("Muzlatilgan kun")
    reason = models.CharField(max_length=200, blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Freeze: {self.membership.user} — {self.date}"
