"""
Lager qoidalari. Barcha raqamlar admin paneldagi "Lager sozlamalari"dan (control.CampSettings)
olinadi — qoidani o'zgartirish uchun kod yozish shart emas.

Funksiyalar ixtiyoriy `c` (sozlamalar) parametrini oladi; berilmasa joriy sozlamalar ishlatiladi.
"""
import datetime as dt
import random

from apps.control import defaults
from apps.control.models import CampSettings, Phrase, Stage


def current():
    return CampSettings.load()


def _to_minutes(t: dt.time) -> int:
    return t.hour * 60 + t.minute


def _from_minutes(m: int) -> dt.time:
    return dt.time(m // 60, m % 60)


def alarm_time_for_day(start: dt.time, target: dt.time, day_number: int, c=None) -> dt.time:
    """
    Kaizen "silliq o'tish": shift_from_day dan boshlab har kuni −shift_step daqiqa,
    maqsad vaqtga yetgach to'xtaydi.
    """
    c = c or current()
    start_m, target_m = _to_minutes(start), _to_minutes(target)
    if target_m >= start_m or day_number < c.shift_from_day:
        return start
    shifted = start_m - c.shift_step_minutes * (day_number - c.shift_from_day + 1)
    return _from_minutes(max(shifted, target_m))


def video_required(day_number: int, c=None) -> bool:
    c = c or current()
    return bool(c.video_from_day) and day_number >= c.video_from_day


def proof_kind(day_number: int, c=None) -> str:
    return "video" if video_required(day_number, c) else "voice"


def wake_deadline(date: dt.date, alarm: dt.time, tz, c=None) -> dt.datetime:
    c = c or current()
    return dt.datetime.combine(date, alarm, tzinfo=tz) + dt.timedelta(minutes=c.wake_grace_minutes)


def proof_minutes(day_number: int, c=None) -> int:
    c = c or current()
    return c.video_deadline_minutes if video_required(day_number, c) else c.voice_deadline_minutes


def proof_deadline(date: dt.date, alarm: dt.time, tz, day_number: int, c=None) -> dt.datetime:
    return dt.datetime.combine(date, alarm, tzinfo=tz) + dt.timedelta(minutes=proof_minutes(day_number, c))


def is_rest_day(date: dt.date, c=None) -> bool:
    """Yakshanba — uxlash mumkin, ogohlantirish berilmaydi (sozlamada o'chirilishi mumkin)."""
    c = c or current()
    return c.sunday_rest and date.weekday() == 6


def approval_threshold(assigned: int) -> int:
    """3 tekshiruvchidan 2 tasi. Kamroq tekshiruvchi bo'lsa — oddiy ko'pchilik."""
    return assigned // 2 + 1 if assigned else 0


def stages():
    return [
        {"id": s.id, "code": s.icon, "name": s.name, "day": s.day, "description": s.description, "icon": s.icon,
         "award_type": s.award_type, "award": s.get_award_type_display(), "rank": s.rank, "stars": s.stars}
        for s in Stage.objects.all()
    ]


def stage_for(completed_days: int, all_stages=None):
    """Tugatilgan kunlar soniga ko'ra erishilgan eng yuqori bosqich (yoki None)."""
    reached = None
    for s in all_stages if all_stages is not None else stages():
        if completed_days >= s["day"]:
            reached = s
    return reached


def random_phrase() -> str:
    texts = list(Phrase.objects.filter(is_active=True).values_list("text", flat=True))
    return random.choice(texts or defaults.PHRASES)


def in_window(now_local: dt.datetime, start: dt.time, end: dt.time) -> bool:
    return start <= now_local.time() <= end
