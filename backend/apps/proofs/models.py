from django.db import models

from apps.camp.models import DayRecord, Membership


class VideoProof(models.Model):
    """
    3-qadam: 10 soniyalik video krujok (ko'cha/hovli + suv).
    Qizlar uchun "yuzsiz isbot" — muhit videosi + ovoz ("Men uyg'oqman") yetarli.
    """

    class Status(models.TextChoices):
        REVIEWING = "reviewing", "Tekshirilmoqda"
        APPROVED = "approved", "Tasdiqlandi"
        REJECTED = "rejected", "Rad etildi"

    day = models.OneToOneField(DayRecord, on_delete=models.CASCADE, related_name="video")
    telegram_file_id = models.CharField(max_length=255)
    duration = models.PositiveSmallIntegerField(default=0)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.REVIEWING)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Video: {self.day}"


class Review(models.Model):
    """P2P tekshiruv: video faqat bir jinsdagi tasodifiy 3 ishtirokchiga boradi."""

    proof = models.ForeignKey(VideoProof, on_delete=models.CASCADE, related_name="reviews")
    reviewer = models.ForeignKey(Membership, on_delete=models.CASCADE, related_name="reviews_given")
    approved = models.BooleanField(null=True)  # None — hali ovoz bermagan
    assigned_at = models.DateTimeField(auto_now_add=True)
    voted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["proof", "reviewer"], name="one_review_per_reviewer")
        ]

    def __str__(self):
        return f"{self.reviewer.user} -> {self.proof}"
