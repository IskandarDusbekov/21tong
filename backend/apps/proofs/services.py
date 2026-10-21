"""
P2P video tekshiruvi. Qat'iy gender-izolyatsiya: tekshiruvchilar faqat
o'sha oqimdagi va o'sha jinsdagi faol ishtirokchilar orasidan tanlanadi.
"""
import random

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from apps.camp import rules
from apps.camp.models import Membership, Notification
from apps.camp.services import RuleError, _today_record, local_now, notify

from .models import Review, VideoProof


def pick_reviewers(membership: Membership, k=rules.REVIEWERS_PER_PROOF):
    """Bir jinsdagi, o'zidan boshqa, eng kam yuklangan faollardan tasodifiy k ta."""
    candidates = list(
        Membership.objects.filter(
            cohort=membership.cohort,
            tribe__gender=membership.tribe.gender,
            status=Membership.Status.ACTIVE,
        )
        .exclude(pk=membership.pk)
        .annotate(pending=Count("reviews_given", filter=Q(reviews_given__approved__isnull=True)))
    )
    random.shuffle(candidates)  # teng yuklanganlar orasida tasodifiylik
    candidates.sort(key=lambda m: m.pending)
    return candidates[:k]


@transaction.atomic
def submit_video(membership, telegram_file_id, duration=0, now=None):
    """3-qadam: video krujok botga yuklandi."""
    now = local_now(now)
    record = _today_record(membership, now)
    if not record.voice_at:
        raise RuleError("Avval guruhga ovozli xabar yuboring.")
    if not rules.in_window(now, membership.cohort.morning_window_start, membership.cohort.morning_window_end):
        raise RuleError("Tonggi oyna yopiq.")
    if hasattr(record, "video"):
        raise RuleError("Bugungi video allaqachon yuborilgan.")

    proof = VideoProof.objects.create(day=record, telegram_file_id=telegram_file_id, duration=duration)
    reviewers = pick_reviewers(membership)
    if not reviewers:
        # Tekshiruvchi yo'q (juda kichik guruh) — avtomatik tasdiq
        proof.status = VideoProof.Status.APPROVED
        proof.decided_at = timezone.now()
        proof.save(update_fields=["status", "decided_at"])
        return proof
    for reviewer in reviewers:
        review = Review.objects.create(proof=proof, reviewer=reviewer)
        notify(
            reviewer.user, Notification.Kind.REVIEW_REQUEST,
            review_id=review.id, file_id=telegram_file_id,
        )
    return proof


@transaction.atomic
def cast_vote(review: Review, voter: Membership, approved: bool):
    review = Review.objects.select_for_update().select_related("proof__day__membership__user").get(pk=review.pk)
    if review.reviewer_id != voter.pk:
        raise RuleError("Bu video sizga tekshirish uchun yuborilmagan.")
    if review.approved is not None:
        raise RuleError("Siz allaqachon ovoz bergansiz.")
    review.approved = approved
    review.voted_at = timezone.now()
    review.save(update_fields=["approved", "voted_at"])

    proof = review.proof
    if proof.status != VideoProof.Status.REVIEWING:
        return proof
    votes = list(proof.reviews.values_list("approved", flat=True))
    need = rules.approval_threshold(len(votes))
    if votes.count(True) >= need:
        proof.status = VideoProof.Status.APPROVED
    elif votes.count(False) >= need:
        proof.status = VideoProof.Status.REJECTED
    else:
        return proof
    proof.decided_at = timezone.now()
    proof.save(update_fields=["status", "decided_at"])
    owner = proof.day.membership.user
    kind = Notification.Kind.VIDEO_APPROVED if proof.status == VideoProof.Status.APPROVED else Notification.Kind.VIDEO_REJECTED
    notify(owner, kind, day_number=proof.day.day_number)
    return proof
