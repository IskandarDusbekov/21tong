"""
Lagerning asosiy biznes-logikasi. Bot ham, Mini App ham faqat shu funksiyalar orqali
holatni o'zgartiradi — qoidalar bir joyda.
"""
import datetime as dt
from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Gender, User

from . import rules
from .models import Cohort, DayRecord, Freeze, Joker, Membership, Notification, Strike, Tribe


class RuleError(Exception):
    """Qoida buzilganda — xabar foydalanuvchiga ko'rsatiladi."""


def notify(user, kind, **payload):
    return Notification.objects.create(user=user, kind=kind, payload=payload)


def local_now(now=None):
    return timezone.localtime(now or timezone.now())


# --- Onboarding ---------------------------------------------------------------

@transaction.atomic
def register_user(*, telegram_id, gender, goal, username="", first_name="", referral_code=None):
    """Botdagi anketa yakunlanganda chaqiriladi. Jins keyin o'zgarmaydi."""
    if gender not in Gender.values:
        raise RuleError("Jins noto'g'ri ko'rsatilgan.")
    user, created = User.objects.get_or_create(
        telegram_id=telegram_id,
        defaults={"username": f"tg{telegram_id}", "first_name": first_name, "telegram_username": username},
    )
    if user.gender and user.gender != gender:
        raise RuleError("Jinsni o'zgartirib bo'lmaydi.")
    if user.status in (User.Status.APPROVED, User.Status.REJECTED):
        return user

    user.gender = gender
    user.goal = goal.strip()
    user.telegram_username = username or user.telegram_username
    user.first_name = first_name or user.first_name
    user.status = User.Status.PENDING
    if referral_code and not user.referred_by_id:
        referrer = User.objects.filter(referral_code=referral_code).exclude(pk=user.pk).first()
        user.referred_by = referrer
    user.save()
    return user


@transaction.atomic
def approve_user(user):
    """Admin tasdiqlaydi. Taklif qilgan do'stga (bir marta) boshlang'ich Joker beriladi."""
    if user.status != User.Status.PENDING:
        return False
    user.status = User.Status.APPROVED
    user.approved_at = timezone.now()
    user.save(update_fields=["status", "approved_at"])
    notify(user, Notification.Kind.APPROVED)

    # Shartli UPDATE — parallel tasdiqlarda ham Joker faqat bir marta beriladi
    granted = User.objects.filter(pk=user.referred_by_id, referral_joker_granted=False).update(
        referral_joker_granted=True
    )
    if granted:
        referrer = User.objects.get(pk=user.referred_by_id)
        Joker.objects.create(user=referrer, source=Joker.Source.REFERRAL)
        notify(referrer, Notification.Kind.JOKER_GRANTED, source="referral", friend=str(user))
    return True


def reject_user(user):
    if user.status != User.Status.PENDING:
        return False
    user.status = User.Status.REJECTED
    user.save(update_fields=["status"])
    notify(user, Notification.Kind.REJECTED)
    return True


@transaction.atomic
def join_cohort(user, cohort: Cohort, start_wake_time: dt.time, target_wake_time: dt.time):
    """Foydalanuvchini o'z jinsidagi va vaqtidagi qabilaga joylashtiradi."""
    if user.status != User.Status.APPROVED:
        raise RuleError("Avval admin tasdig'idan o'tishingiz kerak.")
    if not user.gender:
        raise RuleError("Jins ko'rsatilmagan.")
    if cohort.status != Cohort.Status.RECRUITING:
        raise RuleError("Bu oqimga qabul yopilgan.")
    if target_wake_time > start_wake_time:
        raise RuleError("Maqsad vaqti boshlang'ich vaqtdan kech bo'lishi mumkin emas.")
    tribe, _ = Tribe.objects.get_or_create(cohort=cohort, gender=user.gender, start_wake_time=start_wake_time)
    membership, created = Membership.objects.get_or_create(
        user=user, cohort=cohort, defaults={"tribe": tribe, "target_wake_time": target_wake_time}
    )
    if not created:
        raise RuleError("Siz bu oqimga allaqachon qo'shilgansiz.")
    return membership


# --- Kunlik zanjir ------------------------------------------------------------

def active_membership(user):
    return (
        Membership.objects.select_related("cohort", "tribe", "user")
        .filter(user=user, status=Membership.Status.ACTIVE, cohort__status=Cohort.Status.RUNNING)
        .first()
    )


def ensure_day_record(membership: Membership, date: dt.date):
    day_number = membership.cohort.day_number(date)
    if day_number is None:
        raise RuleError("Bugun oqim kunlariga kirmaydi.")
    alarm = rules.alarm_time_for_day(membership.tribe.start_wake_time, membership.target_wake_time, day_number)
    record, _ = DayRecord.objects.get_or_create(
        membership=membership, date=date, defaults={"day_number": day_number, "alarm_time": alarm}
    )
    if record.status == DayRecord.Status.PENDING and hasattr(membership, "freeze") and membership.freeze.date == date:
        record.status = DayRecord.Status.FROZEN
        record.save(update_fields=["status"])
    return record


def _today_record(membership, now):
    record = ensure_day_record(membership, now.date())
    if record.status == DayRecord.Status.FROZEN:
        raise RuleError("Bugun muzlatilgan kun — dam oling.")
    if record.status != DayRecord.Status.PENDING:
        raise RuleError("Bugungi kun allaqachon yakunlangan.")
    return record


def press_wake(membership, now=None):
    """1-qadam: TMA'dagi "Uyg'ondim" tugmasi."""
    now = local_now(now)
    record = _today_record(membership, now)
    if record.woke_at:
        return record
    earliest = dt.datetime.combine(now.date(), membership.cohort.morning_window_start, tzinfo=now.tzinfo)
    earliest = min(earliest, dt.datetime.combine(now.date(), record.alarm_time, tzinfo=now.tzinfo))
    if now < earliest - dt.timedelta(hours=1):
        raise RuleError("Hali juda erta. Budilnik vaqtiga yaqin bosing.")
    record.woke_at = now
    record.save(update_fields=["woke_at"])
    return record


def record_voice(membership, now=None):
    """2-qadam: guruhga ovozli xabar (bot guruhda ko'radi va xabar beradi)."""
    now = local_now(now)
    record = _today_record(membership, now)
    if not record.woke_at:
        raise RuleError("Avval Mini App'da \"Uyg'ondim\" tugmasini bosing.")
    if not rules.in_window(now, membership.cohort.morning_window_start, membership.cohort.morning_window_end):
        raise RuleError("Tonggi oyna yopiq.")
    if not record.voice_at:
        record.voice_at = now
        record.save(update_fields=["voice_at"])
    return record


def day_progress(record: DayRecord):
    video = getattr(record, "video", None)
    return {
        "date": record.date.isoformat(),
        "day_number": record.day_number,
        "alarm_time": record.alarm_time.strftime("%H:%M"),
        "status": record.status,
        "woke": bool(record.woke_at),
        "voice": bool(record.voice_at),
        "video_required": rules.video_required(record.day_number),
        "video": video.status if video else None,
    }


# --- Strike / Joker -----------------------------------------------------------

@dataclass
class StrikeResult:
    strike: Strike
    joker_used: bool
    expelled: bool


@transaction.atomic
def issue_strike(membership, reason, day=None):
    strike = Strike.objects.create(membership=membership, reason=reason, day=day)
    joker = Joker.objects.select_for_update().filter(user=membership.user, used_on__isnull=True).first()
    if joker:
        joker.used_on = strike
        joker.save(update_fields=["used_on"])
        strike.cancelled_by_joker = True
        strike.save(update_fields=["cancelled_by_joker"])
        notify(membership.user, Notification.Kind.JOKER_USED, reason=reason)
        return StrikeResult(strike, joker_used=True, expelled=False)

    count = membership.active_strikes
    notify(membership.user, Notification.Kind.STRIKE, reason=reason, count=count, max=rules.MAX_STRIKES)
    if count >= rules.MAX_STRIKES:
        membership.status = Membership.Status.EXPELLED
        membership.left_at = timezone.now()
        membership.save(update_fields=["status", "left_at"])
        notify(
            membership.user, Notification.Kind.EXPELLED,
            tribe_chat_id=membership.tribe.telegram_chat_id,
        )
        return StrikeResult(strike, joker_used=False, expelled=True)
    return StrikeResult(strike, joker_used=False, expelled=False)


def _failure_reason(record: DayRecord, tz):
    if not record.woke_at or record.woke_at > rules.wake_deadline(record.date, record.alarm_time, tz):
        return Strike.Reason.LATE
    if not record.voice_at:
        return Strike.Reason.NO_VOICE
    if rules.video_required(record.day_number):
        video = getattr(record, "video", None)
        if video is None:
            return Strike.Reason.NO_VIDEO
        # Jamoa ovoz bermay qolgan video — foyda ishtirokchi tomonida (tasdiqlangan deb hisoblanadi)
        if video.status == video.Status.REJECTED:
            return Strike.Reason.REJECTED
    return None


@transaction.atomic
def evaluate_day(record: DayRecord):
    """Kun yakunida chaqiriladi: Strike, Joker va bosqichni hal qiladi. Idempotent."""
    record = DayRecord.objects.select_for_update().select_related("membership__cohort", "membership__user").get(pk=record.pk)
    membership = record.membership
    if record.status != DayRecord.Status.PENDING or membership.status != Membership.Status.ACTIVE:
        return record

    tz = timezone.get_current_timezone()
    reason = _failure_reason(record, tz)
    if rules.is_rest_day(record.date):
        if reason is None:
            record.status = DayRecord.Status.COMPLETED
            Joker.objects.create(user=membership.user, source=Joker.Source.SUNDAY)
            notify(membership.user, Notification.Kind.JOKER_GRANTED, source="sunday")
        else:
            record.status = DayRecord.Status.REST
    elif reason is None:
        record.status = DayRecord.Status.COMPLETED
    else:
        record.status = DayRecord.Status.FAILED

    record.evaluated_at = timezone.now()
    record.save(update_fields=["status", "evaluated_at"])

    if record.status == DayRecord.Status.FAILED:
        issue_strike(membership, reason, day=record)
    else:
        survived = membership.days.exclude(status__in=[DayRecord.Status.PENDING, DayRecord.Status.FAILED]).count()
        stage = rules.stage_for(survived)
        if stage and stage["day"] == survived:
            notify(membership.user, Notification.Kind.STAGE_UP, **stage)
    return record


# --- Fors-major ---------------------------------------------------------------

def request_freeze(membership, reason="", now=None):
    """Kasallik: butun oqimda 1 marta, faqat kechqurun ertangi kun uchun."""
    now = local_now(now)
    if Freeze.objects.filter(membership=membership).exists():
        raise RuleError("Muzlatish imkoniyatidan allaqachon foydalangansiz.")
    if now.time() < rules.FREEZE_ALLOWED_FROM:
        raise RuleError(f"Muzlatishni faqat kechqurun ({rules.FREEZE_ALLOWED_FROM:%H:%M} dan keyin) oldindan bosish mumkin.")
    tomorrow = now.date() + dt.timedelta(days=1)
    if membership.cohort.day_number(tomorrow) is None:
        raise RuleError("Ertangi kun oqimga kirmaydi.")
    return Freeze.objects.create(membership=membership, date=tomorrow, reason=reason[:200])


def jokers_available(user):
    return Joker.objects.filter(user=user, used_on__isnull=True).count()
