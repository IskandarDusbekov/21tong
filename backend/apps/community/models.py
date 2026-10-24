from django.conf import settings
from django.db import models

from apps.camp.models import Cohort, Membership, Squad


class SquadMessage(models.Model):
    """
    Rota chati (Mini App ichida) — Telegram guruh o'rniga. Faqat matn xabarlari shu yerda saqlanadi;
    raportlar, ogohlantirish va tonggi raport kabi voqealar chat lentasida jonli hisoblanadi.
    Yozish faqat oyna ochiq bo'lganda (tong/kechqurun) — server tekshiradi.
    """

    squad = models.ForeignKey(Squad, on_delete=models.CASCADE, related_name="messages", verbose_name="Rota")
    author = models.ForeignKey(Membership, null=True, blank=True, on_delete=models.SET_NULL,
                               related_name="messages", verbose_name="Muallif")
    # Admin har bir rotada mentor — paneldan yozadi, oyna yopiq bo'lsa ham.
    mentor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                               related_name="mentor_messages", verbose_name="Mentor (admin)")
    text =models.CharField("Matn", max_length=1000)
    created_at = models.DateTimeField("Vaqt", auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["squad", "created_at"])]
        verbose_name = "Rota chati xabari"
        verbose_name_plural = "Rota chati xabarlari"

    def __str__(self):
        return f"{self.author or self.mentor or 'tizim'}: {self.text[:30]}"


class Reflection(models.Model):
    """Kechki oyna: "Bugungi kun qanday o'tdi?" (uzunligi sozlamada)."""

    membership = models.ForeignKey(Membership, on_delete=models.CASCADE, related_name="reflections",
                                   verbose_name="Ishtirokchi")
    date = models.DateField("Sana")
    text = models.CharField("Matn", max_length=1000)
    created_at = models.DateTimeField("Yozilgan", auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["membership", "date"], name="one_reflection_per_day")
        ]
        ordering = ["-created_at"]
        verbose_name = "Refleksiya"
        verbose_name_plural = "Refleksiyalar"

    def __str__(self):
        return f"{self.membership.user}: {self.text[:30]}"


class Fire(models.Model):
    """Lentadagi refleksiyaga "olov" reaksiyasi."""

    reflection = models.ForeignKey(Reflection, on_delete=models.CASCADE, related_name="fires")
    membership = models.ForeignKey(Membership, on_delete=models.CASCADE, related_name="fires_given")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["reflection", "membership"], name="one_fire_per_member")
        ]
        verbose_name = "Olov"
        verbose_name_plural = "Olovlar"


class Bounty(models.Model):
    """Kunduzgi ixtiyoriy topshiriq (kitob, sport...). Bajarganlar IrodaCoin oladi."""

    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, related_name="bounties", verbose_name="Oqim")
    date = models.DateField("Sana")
    title = models.CharField("Topshiriq", max_length=120)
    description = models.TextField("Tavsif", blank=True)
    reward = models.PositiveIntegerField("Mukofot (IrodaCoin)", default=10)

    class Meta:
        ordering = ["-date"]
        verbose_name = "Kunduzgi topshiriq (Bounty)"
        verbose_name_plural = "Kunduzgi topshiriqlar (Bounty)"

    def __str__(self):
        return f"{self.date}: {self.title}"


class BountyCompletion(models.Model):
    bounty = models.ForeignKey(Bounty, on_delete=models.CASCADE, related_name="completions", verbose_name="Topshiriq")
    membership = models.ForeignKey(Membership, on_delete=models.CASCADE, related_name="bounty_completions",
                                   verbose_name="Ishtirokchi")
    note = models.CharField("Izoh", max_length=200, blank=True)
    created_at = models.DateTimeField("Bajarilgan", auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["bounty", "membership"], name="one_completion_per_bounty")
        ]
        verbose_name = "Bajarilgan topshiriq"
        verbose_name_plural = "Bajarilgan topshiriqlar"


class PhotoChallenge(models.Model):
    """Tonggi rasm chelenji — kunlik, oqim bo'yicha. Har kishi 2 tagacha rasm yuboradi, eng yaxshilari reytingga."""

    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, related_name="photo_challenges", verbose_name="Oqim")
    date = models.DateField("Sana")
    title = models.CharField("Nomi", max_length=120, default="Tonggi rasm chelenji")
    theme = models.CharField("Mavzu", max_length=200, blank=True,
                             help_text="Masalan: «Tong manzarasi» yoki «Mashqdan keyin». Bo'sh bo'lsa — erkin.")
    max_entries = models.PositiveSmallIntegerField("Har kishi nechta rasm", default=2)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["cohort", "date"], name="one_challenge_per_day")]
        ordering = ["-date"]
        verbose_name = "Rasm chelenji"
        verbose_name_plural = "Rasm chelenjilari"

    def __str__(self):
        return f"{self.date}: {self.title}"


class PhotoEntry(models.Model):
    """Rasm chelenjiga yuborilgan bitta rasm."""

    challenge = models.ForeignKey(PhotoChallenge, on_delete=models.CASCADE, related_name="entries", verbose_name="Chelenj")
    membership = models.ForeignKey(Membership, on_delete=models.CASCADE, related_name="photo_entries",
                                   verbose_name="Ishtirokchi")
    image = models.ImageField("Rasm", upload_to="photos/%Y/%m/%d/")
    created_at = models.DateTimeField("Yuborilgan", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Chelenj rasmi"
        verbose_name_plural = "Chelenj rasmlari"

    def __str__(self):
        return f"{self.membership.user} — {self.challenge.date}"


class PhotoVote(models.Model):
    """Rasmga ovoz (🔥) — bir kishi bir rasmga bir marta, o'ziga emas."""

    entry = models.ForeignKey(PhotoEntry, on_delete=models.CASCADE, related_name="votes", verbose_name="Rasm")
    voter = models.ForeignKey(Membership, on_delete=models.CASCADE, related_name="photo_votes_given", verbose_name="Ovoz bergan")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["entry", "voter"], name="one_photo_vote_per_member")]
        verbose_name = "Rasmga ovoz"
        verbose_name_plural = "Rasmga ovozlar"


class CoinTransaction(models.Model):
    """IrodaCoin hisob daftari. Balans = summa(amount)."""

    class Reason(models.TextChoices):
        BOUNTY = "bounty", "Bounty"
        ADMIN = "admin", "Admin"
        WAKE = "wake", "Vaqtida uyg'ondi"
        VOICE = "voice", "Ovozli raport"
        WATER = "water", "Iliq suv"
        VIDEO = "video", "Yurish videosi"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="coin_transactions",
                             verbose_name="Foydalanuvchi")
    amount = models.IntegerField("Miqdor")
    reason = models.CharField("Sabab", max_length=16, choices=Reason.choices)
    bounty_completion = models.OneToOneField(
        BountyCompletion, null=True, blank=True, on_delete=models.SET_NULL, related_name="transaction"
    )
    # Kunlik topshiriq uchun berilgan tanga — bir kunda har topshiriqqa faqat bir marta.
    day = models.ForeignKey("camp.DayRecord", null=True, blank=True, on_delete=models.CASCADE,
                            related_name="coin_transactions", verbose_name="Kun")
    created_at = models.DateTimeField("Vaqt", auto_now_add=True)

    class Meta:
        verbose_name = "IrodaCoin amaliyoti"
        verbose_name_plural = "IrodaCoin amaliyotlari"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["day", "reason"], condition=models.Q(day__isnull=False),
                                    name="one_task_reward_per_day"),
        ]
