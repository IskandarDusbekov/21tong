import datetime as dt

from rest_framework import exceptions
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.response import Response

from apps.camp import services
from apps.camp.services import RuleError


def exception_handler(exc, context):
    if isinstance(exc, RuleError):
        return Response({"detail": str(exc)}, status=400)
    return drf_exception_handler(exc, context)


def require(data, *fields):
    missing = [f for f in fields if data.get(f) in (None, "")]
    if missing:
        raise exceptions.ValidationError({f: "Majburiy maydon." for f in missing})
    return [data[f] for f in fields]


def parse_time(value, field):
    try:
        return dt.time.fromisoformat(value)
    except (TypeError, ValueError):
        raise exceptions.ValidationError({field: "Vaqt HH:MM formatida bo'lsin."})


def membership_summary(membership):
    if membership is None:
        return None
    return {
        "id": membership.id,
        "cohort": {"id": membership.cohort_id, "name": membership.cohort.name, "status": membership.cohort.status},
        "tribe": str(membership.tribe),
        "squad": membership.squad.name if membership.squad_id else None,
        "start_wake_time": membership.tribe.start_wake_time.strftime("%H:%M"),
        "target_wake_time": membership.target_wake_time.strftime("%H:%M"),
        "status": membership.status,
        "strikes": membership.active_strikes,
        "freezes_left": services.freezes_left(membership),
    }
