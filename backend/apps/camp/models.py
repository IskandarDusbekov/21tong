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

    name = models.CharField("Nomi", max_length=100)
    start_date = models.DateField("Boshlanish sanasi")
    duration_days = models.PositiveSmallIntegerField("Davomiyligi (kun)", default=21)
    status = models.CharField("Holati", max_length=16, choices=Status.choices, default=Status.RECRUITING)

    # "Oyna" usuli: rota chatlari faqat shu oraliqlarda ochiq
    morning_window_start = models.TimeField("Tonggi oyna: boshlanishi", default=dt.time(5, 30))
    morning_window_end = models.TimeField("Tonggi oyna: tugashi", default=dt.time(7, 30))
    evening_window_start = models.TimeField("Kechki oyna: boshlanishi", default=dt.time(20, 30))
    evening_window_end = models.TimeField("Kechki oyna: tugashi", default=dt.time(21, 30))

    created_at = models.DateTimeField("Yaratilgan", auto_now_add=True)

    class Meta:
        ordering = ["-start_date"]
        verbose_name = "Oqim"
        verbose_name_plural = "Oqimlar"

    def __str__(self):
        return self.name

    @property
    def end_date(self):
        return self.start_date + dt.timedelta(days=self.duration_days - 1)

    def day_number(self, date):
        """Oqimning nechanchi kuni (1 dan boshlanadi). Oqimdan tashqarida None."""
        n = (date - self.start_date).days + 1
        return n if 1 <= n <= self.duration_days else None


class WakeSlot(models.Model):
    """
    Tayyor rota vaqti — admin oqim uchun oldindan 3–4 tasini yaratadi (masalan "06:00 → 05:00").
    Foydalanuvchi arizada shulardan birini tanlaydi; budilnik shu vaqtga moslashadi.
    """

    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, related_name="slots", verbose_name="Oqim")
    start_wake_time = models.TimeField("Boshlang'ich uyg'onish")
    target_wake_time = models.TimeField("Maqsad uyg'onish")
    title = models.CharField("Nomi", max_length=60, blank=True, help_text="Masalan: «Erta qushlar». Bo'sh bo'lsa vaqt ko'rsatiladi.")
    is_open = models.BooleanField("Tanlash mumkin", default=True)

    class Meta:
        ordering = ["start_wake_time", "target_wake_time"]
        verbose_name = "Rota vaqti"
        verbose_name_plural = "Rota vaqtlari"
        constraints = [
            models.UniqueConstraint(fields=["cohort", "start_wake_time", "target_wake_time"], name="unique_slot")
        ]

    def __str__(self):
        label = f"{self.start_wake_time:%H:%M} → {self.target_wake_time:%H:%M}"
        return f"{self.title} ({label})" if self.title else label


class Tribe(models.Model):
    """
    Qabila — bir xil boshlang'ich uyg'onish vaqtidagi, bir jinsdagi ishtirokchilar.
    Masalan: "7:00 Qabilasi (Yigitlar)". Ichida 7 kishilik rotalar bo'ladi.
    """

    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, related_name="tribes", verbose_name="Oqim")
    gender = models.CharField("Jins", max_length=1, choices=Gender.choices)
    start_wake_time = models.TimeField("Boshlang'ich uyg'onish vaqti")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["cohort", "gender", "start_wake_time"], name="unique_tribe_per_slot"
            )
        ]
        ordering = ["start_wake_time", "gender"]
        verbose_name = "Qabila"
        verbose_name_plural = "Qabilalar"

    def __str__(self):
        return f"{self.start_wake_time:%H:%M} Qabilasi ({self.get_gender_display()}lar)"


class Squad(models.Model):
    """
    Rota — qabila ichidagi kichik jamoa (standart 7 kishi). Har rotaning Mini App ichida o'z chati bor:
    raportlar, ogohlantirishlar va P2P tekshiruv birinchi navbatda rota ichida ko'rinadi.
    """

    tribe = models.ForeignKey(Tribe, on_delete=models.CASCADE, related_name="squads", verbose_name="Qabila")
    number = models.PositiveSmallIntegerField("Raqami")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["tribe", "number"], name="unique_squad_number")]
        ordering = ["tribe", "number"]
        verbose_name = "Rota"
        verbose_name_plural = "Rotalar"

    def __str__(self):
        return f"{self.number}-rota · {self.tribe}"

    @property
    def name(self):
        return f"{self.number}-rota"


class Membership(models.Model):
    """Foydalanuvchining bitta oqimdagi ishtiroki."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Faol"
        EXPELLED = "expelled", "Chiqarilgan"
        FINISHED = "finished", "Oqimni tugatgan"
        MENTOR = "mentor", "Mentor"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships",
                             verbose_name="Foydalanuvchi")
    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, related_name="memberships", verbose_name="Oqim")
    tribe = models.ForeignKey(Tribe, on_delete=models.PROTECT, related_name="memberships", verbose_name="Qabila")
    squad = models.ForeignKey(Squad, null=True, blank=True, on_delete=models.SET_NULL, related_name="memberships",
                              verbose_name="Rota")
    target_wake_time = models.TimeField("Maqsad qilingan uyg'onish vaqti")
    status = models.CharField("Holati", max_length=16, choices=Status.choices, default=Status.ACTIVE)
    joined_at = models.DateTimeField("Qo'shilgan", auto_now_add=True)
    left_at = models.DateTimeField("Chiqqan", null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "cohort"], name="one_membership_per_cohort")
        ]
        verbose_name = "Ishtirokchi"
        verbose_name_plural = "Ishtirokchilar"

    def __str__(self):
        return f"{self.user} @ {self.cohort}"

    @property
    def active_strikes(self):
        return self.strikes.filter(cancelled_by_immunity=False, revoked=False).count()


class DayRecord(models.Model):
    """Ishtirokchining bitta kundagi holati: budilnik vaqti, uyg'onish va raport."""

    class Status(models.TextChoices):
        PENDING = "pending", "Kutilmoqda"
        COMPLETED = "completed", "Bajarildi"
        FAILED = "failed", "Bajarilmadi"
        REST = "rest", "Yakshanba dam olish"
        FROZEN = "frozen", "Muzlatilgan"

    membership = models.ForeignKey(Membership, on_delete=models.CASCADE, related_name="days", verbose_name="Ishtirokchi")
    date = models.DateField("Sana")
    day_number = models.PositiveSmallIntegerField("Kun")
    alarm_time = models.TimeField("Budilnik")

    woke_at = models.DateTimeField("Uyg'ondi", null=True, blank=True)
    # Uyg'ongach beriladigan, ovoz chiqarib o'qiladigan gap. Har kuni har kimga tasodifiy —
    # eski yozuvni qayta yuborib aldab bo'lmaydi, tekshiruvchilar gapni solishtiradi.
    phrase = models.CharField("O'qiladigan gap", max_length=200, blank=True)
    voice_at = models.DateTimeField("Ovozli raport", null=True, blank=True)
    voice_file_id = models.CharField(max_length=255, blank=True)
    # Kech kelgan raport ham qabul qilinadi (chatga tushadi), lekin kun bajarilgan hisoblanmaydi.
    voice_late = models.BooleanField("Ovozli raport kech keldi", default=False)
    # Video talab qilinadigan kunlarda raport — proofs.VideoProof orqali

    # Qo'mondonlik raportni ko'zdan kechirsa — chatda "Admin tekshirdi" yozuvi hammaga ko'rinadi.
    admin_reviewed_at = models.DateTimeField("Admin tekshirdi", null=True, blank=True)

    status = models.CharField("Holati", max_length=16, choices=Status.choices, default=Status.PENDING)
    evaluated_at = models.DateTimeField("Baholangan", null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["membership", "date"], name="one_record_per_day")
        ]
        ordering = ["date"]
        verbose_name = "Kunlik yozuv"
        verbose_name_plural = "Kunlik yozuvlar"

    def __str__(self):
        return f"{self.membership.user} — {self.day_number}-kun ({self.date})"


class Strike(models.Model):
    """Ogohlantirish."""

    class Reason(models.TextChoices):
        LATE = "late", "Vaqtida turmadi"
        NO_VOICE = "no_voice", "Ovozli raport yo'q"
        NO_VIDEO = "no_video", "Video raport yo'q"
        REJECTED = "rejected", "Rota tasdiqlamadi"
        ADMIN = "admin", "Qo'mondonlik qarori"

    membership = models.ForeignKey(Membership, on_delete=models.CASCADE, related_name="strikes", verbose_name="Ishtirokchi")
    day = models.ForeignKey(DayRecord, null=True, blank=True, on_delete=models.SET_NULL, related_name="strikes",
                            verbose_name="Kun")
    reason = models.CharField("Sabab", max_length=16, choices=Reason.choices)
    cancelled_by_immunity = models.BooleanField("Immunitet bilan o'chirildi", default=False)
    revoked = models.BooleanField("Admin bekor qildi", default=False)
    created_at = models.DateTimeField("Berilgan", auto_now_add=True)

    class Meta:
        verbose_name = "Ogohlantirish"
        verbose_name_plural = "Ogohlantirishlar"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.membership.user} — {self.get_reason_display()}"


class Immunity(models.Model):
    """Immunitet: keyingi 1 ta ogohlantirishni o'chiradi. Foydalanuvchiga tegishli (oqimlar orasida saqlanadi)."""

    class Source(models.TextChoices):
        REFERRAL = "referral", "Do'st taklifi"
        SUNDAY = "sunday", "Yakshanba barvaqt turish"
        ADMIN = "admin", "Qo'mondonlik"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="immunities",
                             verbose_name="Foydalanuvchi")
    source = models.CharField("Manba", max_length=16, choices=Source.choices)
    granted_at = models.DateTimeField("Berilgan", auto_now_add=True)
    used_on = models.OneToOneField(Strike, null=True, blank=True, on_delete=models.SET_NULL, related_name="immunity",
                                   verbose_name="Qaysi ogohlantirishga ishlatildi")

    class Meta:
        verbose_name = "Immunitet"
        verbose_name_plural = "Immunitetlar"
        ordering = ["-granted_at"]

    def __str__(self):
        return f"Immunitet ({self.get_source_display()}) — {self.user}"


class Award(models.Model):
    """Bosqichga yetganda beriladigan mukofot (pogon, medal yoki sertifikat). Raqami o'zgarmaydi."""

    membership = models.ForeignKey(Membership, on_delete=models.CASCADE, related_name="awards", verbose_name="Ishtirokchi")
    stage = models.ForeignKey("control.Stage", on_delete=models.PROTECT, related_name="awards", verbose_name="Bosqich")
    issued_at = models.DateTimeField("Berilgan", auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["membership", "stage"], name="one_award_per_stage")]
        ordering = ["stage__day"]
        verbose_name = "Mukofot"
        verbose_name_plural = "Mukofotlar"

    def __str__(self):
        return f"{self.membership.user} — {self.stage}"

    @property
    def number(self):
        return f"21T-{self.issued_at:%y}-{self.pk:05d}"


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
        STRIKE = "strike", "Ogohlantirish"
        IMMUNITY_USED = "immunity_used", "Immunitet ishlatildi"
        IMMUNITY_GRANTED = "immunity_granted", "Immunitet berildi"
        EXPELLED = "expelled", "Chiqarildi"
        STAGE_UP = "stage_up", "Yangi bosqich"
        BROADCAST = "broadcast", "Ommaviy xabar"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications",
                             verbose_name="Kimga")
    kind = models.CharField("Turi", max_length=32, choices=Kind.choices)
    payload = models.JSONField("Ma'lumot", default=dict, blank=True)
    created_at = models.DateTimeField("Yaratilgan", auto_now_add=True)
    sent_at = models.DateTimeField("Yuborilgan", null=True, blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["sent_at", "created_at"])]
        verbose_name = "Bot xabari navbati"
        verbose_name_plural = "Bot xabarlari navbati"


class Freeze(models.Model):
    """Fors-major (kasallik): oqimda sozlamadagi soncha, faqat kechqurun ertangi kun uchun bosiladi."""

    membership = models.ForeignKey(Membership, on_delete=models.CASCADE, related_name="freezes", verbose_name="Ishtirokchi")
    date = models.DateField("Muzlatilgan kun")
    reason = models.CharField("Sabab", max_length=200, blank=True)
    requested_at = models.DateTimeField("So'ralgan", auto_now_add=True)

    class Meta:
        verbose_name = "Muzlatish (kasallik)"
        verbose_name_plural = "Muzlatishlar (kasallik)"

    def __str__(self):
        return f"{self.membership.user} — {self.date}"
