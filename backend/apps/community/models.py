from django.conf import settings
from django.db import models

from apps.camp.models import Cohort, Membership


class Reflection(models.Model):
    """Kechki oyna: "Bugungi kun qanday o'tdi?" (maks 200 belgi)."""

    membership = models.ForeignKey(Membership, on_delete=models.CASCADE, related_name="reflections")
    date = models.DateField()
    text = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["membership", "date"], name="one_reflection_per_day")
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.membership.user}: {self.text[:30]}"


class Fire(models.Model):
    """Lentadagi refleksiyaga "🔥" reaksiyasi."""

    reflection = models.ForeignKey(Reflection, on_delete=models.CASCADE, related_name="fires")
    membership = models.ForeignKey(Membership, on_delete=models.CASCADE, related_name="fires_given")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["reflection", "membership"], name="one_fire_per_member")
        ]


class Bounty(models.Model):
    """Kunduzgi ixtiyoriy topshiriq (kitob, sport...). Bajarganlar IrodaCoin oladi."""

    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, related_name="bounties")
    date = models.DateField()
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    reward = models.PositiveIntegerField(default=10)

    class Meta:
        ordering = ["-date"]
        verbose_name_plural = "bounties"

    def __str__(self):
        return f"{self.date}: {self.title}"


class BountyCompletion(models.Model):
    bounty = models.ForeignKey(Bounty, on_delete=models.CASCADE, related_name="completions")
    membership = models.ForeignKey(Membership, on_delete=models.CASCADE, related_name="bounty_completions")
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["bounty", "membership"], name="one_completion_per_bounty")
        ]


class CoinTransaction(models.Model):
    """IrodaCoin hisob daftari. Balans = summa(amount)."""

    class Reason(models.TextChoices):
        BOUNTY = "bounty", "Bounty"
        ADMIN = "admin", "Admin"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="coin_transactions")
    amount = models.IntegerField()
    reason = models.CharField(max_length=16, choices=Reason.choices)
    bounty_completion = models.OneToOneField(
        BountyCompletion, null=True, blank=True, on_delete=models.SET_NULL, related_name="transaction"
    )
    created_at = models.DateTimeField(auto_now_add=True)
