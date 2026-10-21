"""Kirish, bosh sahifa, arizalar, ishtirokchilar, rotalar."""
from django.contrib.auth import authenticate, login, logout
from django.db.models import Count, Q
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from rest_framework import exceptions
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.accounts.models import User
from apps.camp import rules, services
from apps.camp.models import Cohort, DayRecord, Immunity, Membership, Notification, Squad, Strike
from apps.proofs.models import VideoProof

from .base import PanelView, hhmm, person


# --- Kirish ------------------------------------------------------------------------

@method_decorator(ensure_csrf_cookie, name="dispatch")
class SessionView(PanelView):
    """GET — kim kirgan (CSRF cookie ham o'rnatiladi); POST — kirish; DELETE — chiqish."""

    permission_classes = [AllowAny]

    def get(self, request):
        u = request.user  # DRF sozlamasida kirmagan foydalanuvchi — None
        if not (u and u.is_authenticated and u.is_staff):
            return Response({"user": None, "csrf": get_token(request)})
        return Response({"user": {"name": u.get_full_name() or u.username, "username": u.username}, "csrf": get_token(request)})

    def post(self, request):
        user = authenticate(request, username=request.data.get("username", ""), password=request.data.get("password", ""))
        if user is None or not user.is_staff:
            raise exceptions.AuthenticationFailed("Login yoki parol noto'g'ri (yoki admin huquqi yo'q).")
        login(request, user)
        return self.get(request)

    def delete(self, request):
        logout(request)
        return Response({"user": None})


# --- Bosh sahifa ---------------------------------------------------------------------

EVENT_KINDS = [
    Notification.Kind.NEW_APPLICATION, Notification.Kind.STRIKE, Notification.Kind.EXPELLED,
    Notification.Kind.STAGE_UP, Notification.Kind.IMMUNITY_USED, Notification.Kind.IMMUNITY_GRANTED,
    Notification.Kind.APPROVED,
]


def completion_series(cohort):
    """Oqimning har bir kuni uchun: bajarganlar, ogohlantirish olganlar, dam/muzlatilgan, kutilayotganlar."""
    rows = (
        DayRecord.objects.filter(membership__cohort=cohort)
        .values("day_number")
        .annotate(
            done=Count("id", filter=Q(status=DayRecord.Status.COMPLETED)),
            failed=Count("id", filter=Q(status=DayRecord.Status.FAILED)),
            rest=Count("id", filter=Q(status__in=[DayRecord.Status.REST, DayRecord.Status.FROZEN])),
            pending=Count("id", filter=Q(status=DayRecord.Status.PENDING)),
        )
        .order_by("day_number")
    )
    return list(rows)


class DashboardView(PanelView):
    def get(self, request):
        today = services.local_now().date()
        running = list(Cohort.objects.filter(status=Cohort.Status.RUNNING).order_by("start_date"))
        active = Membership.objects.filter(status=Membership.Status.ACTIVE, cohort__status=Cohort.Status.RUNNING)
        squads = Squad.objects.filter(tribe__cohort__in=running).select_related("tribe__cohort")
        reports = [{"id": s.id, **services.squad_report(s, today)} for s in squads]
        done = sum(r["done"] for r in reports)
        woke_only = sum(1 for r in reports for m in r["members"] if m["status"] == "woke")
        absent = sum(1 for r in reports for m in r["members"] if m["status"] == "absent")

        events = Notification.objects.filter(kind__in=EVENT_KINDS).select_related("user").order_by("-created_at")[:15]
        c = rules.current()
        return Response({
            "today": today,
            "kpis": {
                "pending_applications": User.objects.filter(status=User.Status.PENDING).count(),
                "active": active.count(),
                "done_today": done,
                "woke_only": woke_only,
                "absent": absent,
                "strikes_today": Strike.objects.filter(created_at__date=today, revoked=False, cancelled_by_immunity=False).count(),
                "videos_reviewing": VideoProof.objects.filter(status=VideoProof.Status.REVIEWING).count(),
                "expelled_total": Membership.objects.filter(status=Membership.Status.EXPELLED, cohort__in=running).count(),
            },
            "cohorts": [
                {
                    "id": co.id, "name": co.name, "day": co.day_number(today), "duration": co.duration_days,
                    "start_date": co.start_date, "end_date": co.end_date,
                    "active": co.memberships.filter(status=Membership.Status.ACTIVE).count(),
                    "expelled": co.memberships.filter(status=Membership.Status.EXPELLED).count(),
                    "series": completion_series(co),
                }
                for co in running
            ],
            "recruiting": [
                {"id": co.id, "name": co.name, "start_date": co.start_date, "members": co.memberships.count()}
                for co in Cohort.objects.filter(status=Cohort.Status.RECRUITING)
            ],
            "squads": reports,
            "events": [
                {"id": n.id, "kind": n.kind, "label": n.get_kind_display(), "user": person(n.user),
                 "payload": n.payload, "at": n.created_at}
                for n in events
            ],
            "rules": {"max_strikes": c.max_strikes, "voice_deadline": c.voice_deadline_minutes, "video_from_day": c.video_from_day},
        })


# --- Arizalar ----------------------------------------------------------------------

def application(u):
    return {
        **person(u),
        "goal": u.goal,
        "slot": str(u.preferred_slot) if u.preferred_slot_id else None,
        "slot_cohort": u.preferred_slot.cohort.name if u.preferred_slot_id else None,
        "status": u.status,
        "status_label": u.get_status_display(),
        "current_wake_time": hhmm(u.current_wake_time),
        "target_wake_time": hhmm(u.target_wake_time),
        "referred_by": str(u.referred_by) if u.referred_by_id else None,
        "created_at": u.date_joined,
        "approved_at": u.approved_at,
    }


class ApplicationsView(PanelView):
    def get(self, request):
        status = request.query_params.get("status", User.Status.PENDING)
        qs = User.objects.filter(telegram_id__isnull=False).select_related("referred_by", "preferred_slot__cohort").order_by("-date_joined")
        if status != "all":
            qs = qs.filter(status=status)
        counts = dict(User.objects.filter(telegram_id__isnull=False).values_list("status").annotate(n=Count("id")))
        return Response({"items": [application(u) for u in qs[:300]], "counts": counts})


class ApplicationDecisionView(PanelView):
    def post(self, request, pk, decision):
        user = get_object_or_404(User, pk=pk)
        ok = services.approve_user(user) if decision == "approve" else services.reject_user(user)
        if not ok:
            raise exceptions.ValidationError({"detail": "Bu ariza allaqachon ko'rib chiqilgan."})
        user.refresh_from_db()
        m = user.memberships.select_related("squad", "tribe").first()
        return Response({**application(user), "placed": f"{m.squad.name} · {m.tribe}" if m and m.squad_id else None})


# --- Ishtirokchilar -----------------------------------------------------------------

def member_row(m, today):
    return {
        "id": m.id,
        "user": person(m.user),
        "cohort": {"id": m.cohort_id, "name": m.cohort.name},
        "tribe": str(m.tribe),
        "squad": {"id": m.squad_id, "name": m.squad.name} if m.squad_id else None,
        "status": m.status,
        "status_label": m.get_status_display(),
        "start_wake_time": hhmm(m.tribe.start_wake_time),
        "target_wake_time": hhmm(m.target_wake_time),
        "strikes": m.active_strikes,
        "immunities": services.immunities_available(m.user),
        "today": services.member_report(m, today),
    }


class MembersView(PanelView):
    def get(self, request):
        p = request.query_params
        qs = Membership.objects.select_related("user", "cohort", "tribe", "squad").order_by("cohort", "squad__number", "user__first_name")
        if p.get("cohort"):
            qs = qs.filter(cohort_id=p["cohort"])
        else:
            qs = qs.exclude(cohort__status=Cohort.Status.FINISHED)
        if p.get("squad"):
            qs = qs.filter(squad_id=p["squad"])
        if p.get("gender"):
            qs = qs.filter(tribe__gender=p["gender"])
        if p.get("status"):
            qs = qs.filter(status=p["status"])
        if p.get("q"):
            q = p["q"]
            qs = qs.filter(Q(user__first_name__icontains=q) | Q(user__telegram_username__icontains=q) | Q(user__telegram_id__icontains=q))
        today = services.local_now().date()
        return Response({"items": [member_row(m, today) for m in qs[:500]], "max_strikes": rules.current().max_strikes})


class MemberDetailView(PanelView):
    def get(self, request, pk):
        m = get_object_or_404(Membership.objects.select_related("user", "cohort", "tribe", "squad"), pk=pk)
        today = services.local_now().date()
        strikes = m.strikes.select_related("day").order_by("-created_at")
        return Response({
            **member_row(m, today),
            "goal": m.user.goal,
            "joined_at": m.joined_at,
            "journey": services.journey(m),
            "strikes_list": [
                {"id": s.id, "reason": s.get_reason_display(), "day": s.day.day_number if s.day_id else None,
                 "at": s.created_at, "revoked": s.revoked, "immunity": s.cancelled_by_immunity}
                for s in strikes
            ],
            "awards": [services.award_json(a) for a in m.awards.select_related("stage")],
            "immunities_list": [
                {"id": i.id, "source": i.get_source_display(), "at": i.granted_at, "used": bool(i.used_on_id)}
                for i in Immunity.objects.filter(user=m.user).order_by("-granted_at")
            ],
            "squads": [
                {"id": s.id, "name": s.name}
                for s in Squad.objects.filter(tribe=m.tribe).order_by("number")
            ],
        })


class MemberActionView(PanelView):
    """Bitta ishtirokchi ustidagi amallar."""

    def post(self, request, pk):
        m = get_object_or_404(Membership.objects.select_related("user", "squad", "cohort", "tribe"), pk=pk)
        action = request.data.get("action")
        if action == "give_immunity":
            services.grant_immunity(m.user, Immunity.Source.ADMIN)
            msg = "Immunitet berildi."
        elif action == "give_strike":
            if m.status != Membership.Status.ACTIVE:
                raise exceptions.ValidationError({"detail": "Faqat faol ishtirokchiga ogohlantirish beriladi."})
            result = services.issue_strike(m, Strike.Reason.ADMIN, use_immunity=False)
            msg = "Ogohlantirish berildi." + (" Lagerdan chiqarildi." if result.expelled else "")
        elif action == "revoke_strike":
            strike = get_object_or_404(Strike, pk=request.data.get("strike_id"), membership=m)
            services.revoke_strike(strike)
            msg = "Ogohlantirish bekor qilindi."
        elif action == "expel":
            services.expel(m)
            msg = "Lagerdan chiqarildi."
        elif action == "restore":
            services.restore(m)
            msg = "Lagerga qaytarildi."
        elif action == "mentor":
            m.status = Membership.Status.MENTOR
            m.save(update_fields=["status"])
            msg = "Mentor qilindi."
        elif action == "move_squad":
            squad = get_object_or_404(Squad, pk=request.data.get("squad_id"), tribe=m.tribe)
            m.squad = squad
            m.save(update_fields=["squad"])
            msg = f"{squad.name} ga o'tkazildi."
        elif action == "excuse_day":
            record = get_object_or_404(DayRecord, membership=m, day_number=request.data.get("day_number"))
            services.excuse_day(record)
            msg = f"{record.day_number}-kun uzrli deb belgilandi."
        else:
            raise exceptions.ValidationError({"detail": "Noma'lum amal."})
        return Response({"detail": msg})


# --- Rotalar ------------------------------------------------------------------------

class SquadsView(PanelView):
    def get(self, request):
        today = services.local_now().date()
        qs = Squad.objects.exclude(tribe__cohort__status=Cohort.Status.FINISHED).select_related("tribe__cohort")
        if request.query_params.get("cohort"):
            qs = qs.filter(tribe__cohort_id=request.query_params["cohort"])
        return Response([
            {
                "id": s.id, "cohort": s.tribe.cohort.name, "gender": s.tribe.gender,
                **services.squad_report(s, today),
            }
            for s in qs.order_by("tribe__cohort", "tribe__gender", "tribe__start_wake_time", "number")
        ])
