"""
P2P video tekshiruvi. Qat'iy gender-izolyatsiya: tekshiruvchilar avval o'z rotasidan,
yetmasa — o'sha oqim va o'sha jinsdagi boshqa rotalardan tanlanadi.
"""
import random

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from apps.camp import rules
from apps.camp.models import Membership, Notification
from apps.camp.services import RuleError, local_now, notify, proof_record

from .models import Review, VideoProof


def _least_loaded(qs, k):
    candidates = list(qs.annotate(pending=Count("reviews_given", filter=Q(reviews_given__approved__isnull=True))))
    random.shuffle(candidates)  # teng yuklanganlar orasida tasodifiylik
    candidates.sort(key=lambda m: m.pending)
    return candidates[:k]


def pick_reviewers(membership: Membership, k=None):
    """O'zidan boshqa, eng kam yuklangan k ta faol: avval rotadoshlar, keyin bir jinsdagi boshqalar."""
    k = k or rules.current().reviewers_per_proof
    same_gender = Membership.objects.filter(
        cohort=membership.cohort,
        tribe__gender=membership.tribe.gender,
        status=Membership.Status.ACTIVE,
    ).exclude(pk=membership.pk)
    picked = _least_loaded(same_gender.filter(squad=membership.squad_id), k) if membership.squad_id else []
    if len(picked) < k:
        picked += _least_loaded(same_gender.exclude(pk__in=[m.pk for m in picked]), k - len(picked))
    return picked


@transaction.atomic
def submit_video(membership, telegram_file_id, duration=0, now=None):
    """2-qadam (7-kundan): tashqarida, gapni o'qib yozilgan video krujok botga yuborildi."""
    now = local_now(now)
    record = proof_record(membership, now)
    if not rules.video_required(record.day_number):
        raise RuleError(f"Bugun video shart emas — gapni o'qib, ovozli xabar yuboring. Video {rules.current().video_from_day}-kundan.")
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
            phrase=record.phrase, name=membership.user.first_name, day_number=record.day_number,
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
