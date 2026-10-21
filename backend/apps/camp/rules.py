"""
Lager qoidalari — sof funksiyalar (DB ga tegmaydi), shuning uchun oson test qilinadi.

Konsepsiyadan olingan raqamlar shu yerda jamlangan; qoidani o'zgartirish
kerak bo'lsa, faqat shu faylni tahrirlash kifoya.
"""
import datetime as dt

# Kaizen: har kuni budilnik shuncha daqiqaga oldinga suriladi
SHIFT_STEP_MINUTES = 5
# "7-kun (Moslashgan)": -5 daqiqalik qisqarish va video isbot shu kundan boshlanadi
SHIFT_FROM_DAY = 7
VIDEO_REQUIRED_FROM_DAY = 7
# "Uyg'ondim" tugmasini budilnikdan keyin shuncha daqiqa ichida bosish kerak
WAKE_GRACE_MINUTES = 5
# Raport (ovoz yoki video) budilnikdan keyin shuncha daqiqa ichida yuborilishi shart
PROOF_DEADLINE_MINUTES = 30
# 3 Strikes = Out
MAX_STRIKES = 3
# Har rotada nechta odam
SQUAD_SIZE = 7
# P2P tekshiruv: nechta tekshiruvchi
REVIEWERS_PER_PROOF = 3
# Muzlatishni faqat shu vaqtdan keyin (kechqurun) ertangi kun uchun bosish mumkin
FREEZE_ALLOWED_FROM = dt.time(18, 0)
REFLECTION_MAX_LENGTH = 200

# Uyg'ongach ovoz chiqarib o'qiladigan gaplar (kognitiv uyg'otish + raportni soxtalashtirishdan himoya)
PHRASES = [
    "Men bugun o'z irodamning xo'jayiniman.",
    "Intizom — bu o'zimga bergan va'damni bajarish.",
    "Har bir erta tong — kelajagimga qo'yilgan sarmoya.",
    "Qiyinchilik vaqtinchalik, odat esa umrbod qoladi.",
    "Ko'rpa meni yengolmaydi. Men turdim va harakatdaman.",
    "Bugun kechagidan bir qadam kuchliroqman.",
    "Bahona emas, natija. Men uyg'oqman va tayyorman.",
    "Erta turgan yutadi. Bugun men yutaman.",
    "O'zgarish bugun, aynan shu daqiqada boshlanadi.",
    "Men rotamni tushirib qo'ymayman. Men shu yerdaman.",
    "Uyqum emas, maqsadim meni boshqaradi.",
    "Har tong — yangi imkoniyat. Uni qo'ldan bermayman.",
]

STAGES = [
    # (shu kunni tugatgach, kod, nom)
    (3, "survivor", "Omon qolgan"),
    (7, "adapted", "Moslashgan"),
    (21, "iron_will", "Temir Iroda"),
    (40, "mentor", "Yengilmas / Mentor"),
]


def _to_minutes(t: dt.time) -> int:
    return t.hour * 60 + t.minute


def _from_minutes(m: int) -> dt.time:
    return dt.time(m // 60, m % 60)


def alarm_time_for_day(start: dt.time, target: dt.time, day_number: int) -> dt.time:
    """
    Kaizen "silliq o'tish": SHIFT_FROM_DAY dan boshlab har kuni -5 daqiqa,
    maqsad vaqtga yetgach to'xtaydi.

    >>> alarm_time_for_day(dt.time(7, 0), dt.time(5, 30), 6)
    datetime.time(7, 0)
    >>> alarm_time_for_day(dt.time(7, 0), dt.time(5, 30), 7)
    datetime.time(6, 55)
    >>> alarm_time_for_day(dt.time(7, 0), dt.time(5, 30), 40)
    datetime.time(5, 30)
    """
    start_m, target_m = _to_minutes(start), _to_minutes(target)
    if target_m >= start_m or day_number < SHIFT_FROM_DAY:
        return start
    shifted = start_m - SHIFT_STEP_MINUTES * (day_number - SHIFT_FROM_DAY + 1)
    return _from_minutes(max(shifted, target_m))


def video_required(day_number: int) -> bool:
    return day_number >= VIDEO_REQUIRED_FROM_DAY


def wake_deadline(date: dt.date, alarm: dt.time, tz) -> dt.datetime:
    return dt.datetime.combine(date, alarm, tzinfo=tz) + dt.timedelta(minutes=WAKE_GRACE_MINUTES)


def proof_deadline(date: dt.date, alarm: dt.time, tz) -> dt.datetime:
    return dt.datetime.combine(date, alarm, tzinfo=tz) + dt.timedelta(minutes=PROOF_DEADLINE_MINUTES)


def is_rest_day(date: dt.date) -> bool:
    """Yakshanba — uxlash mumkin, Strike berilmaydi."""
    return date.weekday() == 6


def approval_threshold(assigned: int) -> int:
    """3 tekshiruvchidan 2 tasi. Kamroq tekshiruvchi bo'lsa — oddiy ko'pchilik."""
    return assigned // 2 + 1 if assigned else 0


def stage_for(completed_days: int):
    """Tugatilgan kunlar soniga ko'ra erishilgan eng yuqori bosqich (yoki None)."""
    reached = None
    for days, code, name in STAGES:
        if completed_days >= days:
            reached = {"code": code, "name": name, "day": days}
    return reached


def in_window(now_local: dt.datetime, start: dt.time, end: dt.time) -> bool:
    return start <= now_local.time() <= end
