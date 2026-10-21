from django.db import IntegrityError, transaction
from django.db.models import Count, Q, Sum

from apps.camp import rules
from apps.camp.models import Membership
from apps.camp.services import RuleError, local_now

from .models import Bounty, BountyCompletion, CoinTransaction, Fire, Reflection


def add_reflection(membership, text, now=None):
    """Kechki oyna: "Bugungi kun qanday o'tdi?"."""
    now = local_now(now)
    text = (text or "").strip()
    if not text:
        raise RuleError("Javob bo'sh bo'lmasin.")
    limit = rules.current().reflection_max_length
    if len(text) > limit:
        raise RuleError(f"Maksimal {limit} belgi.")
    cohort = membership.cohort
    if not rules.in_window(now, cohort.evening_window_start, cohort.evening_window_end):
        raise RuleError(f"Kechki oyna {cohort.evening_window_start:%H:%M}–{cohort.evening_window_end:%H:%M} da ochiq.")
    reflection, created = Reflection.objects.get_or_create(
        membership=membership, date=now.date(), defaults={"text": text}
    )
    if not created:
        raise RuleError("Bugun javob yozib bo'lgansiz.")
    return reflection


def _visible(membership):
    """Lenta faqat o'z rotasi ichida (rota bo'lmasa — o'z oqimi va jinsi)."""
    if membership.squad_id:
        return Q(membership__squad=membership.squad_id)
    return Q(membership__cohort=membership.cohort, membership__tribe__gender=membership.tribe.gender)


def feed(membership, date):
    """Lenta: rotadoshlarning bugungi refleksiyalari."""
    return (
        Reflection.objects.filter(_visible(membership), date=date)
        .select_related("membership__user")
        .annotate(
            fire_count=Count("fires"),
            fired_by_me=Count("fires", filter=Q(fires__membership=membership)),
        )
    )


def give_fire(membership, reflection: Reflection):
    if not Reflection.objects.filter(_visible(membership), pk=reflection.pk).exists():
        raise RuleError("Bu refleksiya sizga ko'rinmaydi.")
    if reflection.membership_id == membership.pk:
        raise RuleError("O'zingizga olov bera olmaysiz.")
    fire, _ = Fire.objects.get_or_create(reflection=reflection, membership=membership)
    return fire


@transaction.atomic
def complete_bounty(membership, bounty: Bounty, note=""):
    if bounty.cohort_id != membership.cohort_id:
        raise RuleError("Bu topshiriq sizning oqimingizga tegishli emas.")
    if bounty.date != local_now().date():
        raise RuleError("Bu topshiriq faqat o'z kunida bajariladi.")
    try:
        with transaction.atomic():
            completion = BountyCompletion.objects.create(bounty=bounty, membership=membership, note=note[:200])
    except IntegrityError:
        raise RuleError("Bu topshiriqni allaqachon bajargansiz.")
    CoinTransaction.objects.create(
        user=membership.user, amount=bounty.reward,
        reason=CoinTransaction.Reason.BOUNTY, bounty_completion=completion,
    )
    return completion


def coin_balance(user):
    return CoinTransaction.objects.filter(user=user).aggregate(s=Sum("amount"))["s"] or 0


def leaderboard(membership, limit=20):
    """IrodaCoin reytingi — o'z oqimi va jinsi bo'yicha."""
    return (
        Membership.objects.filter(cohort=membership.cohort, tribe__gender=membership.tribe.gender)
        .exclude(status=Membership.Status.EXPELLED)
        .select_related("user")
        .annotate(coins=Sum("user__coin_transactions__amount", default=0))
        .order_by("-coins", "user__id")[:limit]
    )
