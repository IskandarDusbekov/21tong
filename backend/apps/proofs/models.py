from django.db import models

from apps.camp.models import DayRecord, Membership


class VideoProof(models.Model):
    """
    Video raport (sozlamada yoqilgan kunlarda): tashqarida, gapni o'qib yozilgan video krujok.
    Qizlar uchun "yuzsiz isbot" — muhit videosi + ovoz yetarli.
    """

    class Status(models.TextChoices):
        REVIEWING = "reviewing", "Tekshirilmoqda"
        APPROVED = "approved", "Tasdiqlandi"
        REJECTED = "rejected", "Rad etildi"

    day = models.OneToOneField(DayRecord, on_delete=models.CASCADE, related_name="video", verbose_name="Kun")
    telegram_file_id = models.CharField("Telegram fayl ID", max_length=255)
    duration = models.PositiveSmallIntegerField("Davomiyligi (soniya)", default=0)
    status = models.CharField("Holati", max_length=16, choices=Status.choices, default=Status.REVIEWING)
    uploaded_at = models.DateTimeField("Yuborilgan", auto_now_add=True)
    decided_at = models.DateTimeField("Hal qilingan", null=True, blank=True)

    class Meta:
        verbose_name = "Video raport"
        verbose_name_plural = "Video raportlar"
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"Video: {self.day}"


class Review(models.Model):
    """P2P tekshiruv: video avval rotadoshlarga, faqat bir jinsdagilarga boradi."""

    proof = models.ForeignKey(VideoProof, on_delete=models.CASCADE, related_name="reviews", verbose_name="Video")
    reviewer = models.ForeignKey(Membership, on_delete=models.CASCADE, related_name="reviews_given",
                                 verbose_name="Tekshiruvchi")
    approved = models.BooleanField("Tasdiqladi", null=True)  # None — hali ovoz bermagan
    assigned_at = models.DateTimeField("Yuborilgan", auto_now_add=True)
    voted_at = models.DateTimeField("Ovoz bergan", null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["proof", "reviewer"], name="one_review_per_reviewer")
        ]
        verbose_name = "Tekshiruv"
        verbose_name_plural = "Tekshiruvlar"

    def __str__(self):
        return f"{self.reviewer.user} -> {self.proof}"
