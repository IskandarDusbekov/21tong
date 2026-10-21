"""Bot -> backend API. Hammasi `X-Bot-Secret` bilan himoyalangan."""
from django.core.management import call_command
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.auth import IsBot
from apps.accounts.manifest import render_manifest
from apps.accounts.models import Region, User
from apps.camp import services
from apps.camp.awards import render_award
from apps.camp.models import Award, Cohort, DayRecord, Membership, Notification, WakeSlot
from apps.control.models import BotMessage, CampSettings
from apps.proofs import services as proof_services
from apps.proofs.models import Review

from .common import membership_summary, parse_time, require


class BotView(APIView):
    permission_classes = [IsBot]

    def get_user(self, telegram_id):
        return get_object_or_404(User, telegram_id=telegram_id)

    def get_active(self, telegram_id):
        membership = services.active_membership(self.get_user(telegram_id))
        if membership is None:
            raise exceptions.ValidationError({"detail": "Siz hozir faol oqimda emassiz."})
        return membership


def user_payload(user):
    membership = user.memberships.select_related("cohort", "tribe", "squad").order_by("-joined_at").first()
    upcoming = services.upcoming_membership(user)
    return {
        "telegram_id": user.telegram_id,
        "name": user.first_name or user.display_name,
        "full_name": user.display_name,
        "upcoming": services.placement_payload(upcoming) if upcoming else None,
        "status": user.status,
        "gender": user.gender,
        "goal": user.goal,
        "referral_code": user.referral_code,
        "immunities": services.immunities_available(user),
        "membership": membership_summary(membership),
    }


def proof_payload(membership, record):
    """Raport qabul qilingach bot uchun javob (bot foydalanuvchiga tasdiq yuboradi)."""
    return {
        **services.day_progress(record),
        "name": membership.user.first_name or str(membership.user),
        "squad": membership.squad.name if membership.squad_id else None,
    }


class ConfigView(BotView):
    """Admin paneldagi bot xabarlari va lager sozlamalari — bot ularni keshlab ishlatadi."""

    def get(self, request):
        c = CampSettings.load()
        return Response({
            "settings": {**c.template_vars(), "registration_open": c.registration_open},
            "messages": dict(BotMessage.objects.values_list("key", "text")),
            "regions": [{"value": v, "label": label} for v, label in Region.choices],
        })


# --- Ariza va admin -----------------------------------------------------------

class RegisterView(BotView):
    def post(self, request):
        telegram_id, gender, goal = require(request.data, "telegram_id", "gender", "goal")
        current = request.data.get("current_wake_time")
        target = request.data.get("target_wake_time")
        d = request.data
        user = services.register_user(
            telegram_id=int(telegram_id), gender=gender, goal=goal,
            username=d.get("username", ""),
            first_name=d.get("first_name", ""), last_name=d.get("last_name", ""), region=d.get("region", ""),
            slot_id=d.get("slot_id"),
            referral_code=d.get("referral_code"),
            current_wake_time=parse_time(current, "current_wake_time") if current else None,
            target_wake_time=parse_time(target, "target_wake_time") if target else None,
            tg_first_name=d.get("tg_first_name", ""), tg_last_name=d.get("tg_last_name", ""),
            tg_language=d.get("tg_language", ""), tg_is_premium=bool(d.get("tg_is_premium")),
        )
        return Response(user_payload(user), status=201)


class UserView(BotView):
    def get(self, request, telegram_id):
        return Response(user_payload(self.get_user(telegram_id)))


class ApproveView(BotView):
    """Admin Telegram'dagi "Qabul" tugmasini bosdi (adminlikni bot tekshiradi)."""

    def post(self, request, telegram_id):
        user = self.get_user(telegram_id)
        if not services.approve_user(user):
            raise exceptions.ValidationError({"detail": f"Ariza allaqachon ko'rib chiqilgan ({user.get_status_display()})."})
        return Response(user_payload(user))


class RejectView(BotView):
    def post(self, request, telegram_id):
        user = self.get_user(telegram_id)
        if not services.reject_user(user):
            raise exceptions.ValidationError({"detail": f"Ariza allaqachon ko'rib chiqilgan ({user.get_status_display()})."})
        return Response(user_payload(user))


class PendingApplicationsView(BotView):
    def get(self, request):
        users = User.objects.filter(status=User.Status.PENDING).order_by("date_joined")[:50]
        return Response([{"telegram_id": u.telegram_id, **services.application_payload(u)} for u in users])


class ManifestView(BotView):
    def get(self, request, telegram_id):
        user = self.get_user(telegram_id)
        if not user.goal:
            raise exceptions.ValidationError({"detail": "Maqsad hali yozilmagan."})
        return HttpResponse(render_manifest(user), content_type="image/png")


class SlotsView(BotView):
    """Arizada tanlanadigan tayyor rota vaqtlari."""

    def get(self, request):
        today = services.local_now().date()
        return Response([services.slot_json(s, today) for s in services.open_slots()])


class RecruitingCohortsView(BotView):
    def get(self, request):
        cohorts = Cohort.objects.filter(status=Cohort.Status.RECRUITING).order_by("start_date")
        return Response([{"id": c.id, "name": c.name, "start_date": c.start_date} for c in cohorts])


class JoinView(BotView):
    def post(self, request):
        if request.data.get("slot_id"):
            telegram_id, slot_id = require(request.data, "telegram_id", "slot_id")
            slot = get_object_or_404(WakeSlot, pk=slot_id, is_open=True)
            m = services.join_slot(self.get_user(telegram_id), slot)
            return Response(services.placement_payload(m), status=201)
        telegram_id, cohort_id, start, target = require(
            request.data, "telegram_id", "cohort_id", "start_wake_time", "target_wake_time"
        )
        membership = services.join_cohort(
            self.get_user(telegram_id),
            get_object_or_404(Cohort, pk=cohort_id),
            parse_time(start, "start_wake_time"),
            parse_time(target, "target_wake_time"),
        )
        return Response(membership_summary(membership), status=201)


# --- Tonggi zanjir --------------------------------------------------------------

class WakeView(BotView):
    """Budilnik xabaridagi "Uyg'ondim" tugmasi. Javobda bugungi gap va raport turi."""

    def post(self, request):
        (telegram_id,) = require(request.data, "telegram_id")
        membership = self.get_active(telegram_id)
        return Response(services.day_progress(services.press_wake(membership)))


class VoiceView(BotView):
    """1–6 kunlar: gap o'qilgan ovozli raport, botga shaxsiy yuborilgan."""

    def post(self, request):
        telegram_id, file_id = require(request.data, "telegram_id", "file_id")
        user = self.get_user(telegram_id)
        membership = services.active_membership(user)
        if membership is None:
            # Oqim hali boshlanmagan — mashq raporti (yangi kelganlar qanday yuborishni o'rganadi)
            if user.status != User.Status.APPROVED:
                raise exceptions.ValidationError({"detail": "Avval arizangiz qabul qilinishi kerak."})
            upcoming = services.upcoming_membership(user)
            return Response({"practice": True, "upcoming": services.placement_payload(upcoming) if upcoming else None})
        record = services.record_voice(membership, file_id)
        return Response(proof_payload(membership, record), status=201)


class VideoView(BotView):
    """7-kundan: tashqarida yozilgan video krujok."""

    def post(self, request):
        telegram_id, file_id = require(request.data, "telegram_id", "file_id")
        membership = self.get_active(telegram_id)
        proof = proof_services.submit_video(membership, file_id, int(request.data.get("duration") or 0))
        return Response({**proof_payload(membership, proof.day), "proof_status": proof.status}, status=201)


class VoteView(BotView):
    def post(self, request, review_id):
        telegram_id, approved = require(request.data, "telegram_id", "approved")
        review = get_object_or_404(Review, pk=review_id)
        voter = get_object_or_404(Membership, user__telegram_id=telegram_id, pk=review.reviewer_id)
        proof = proof_services.cast_vote(review, voter, bool(approved))
        return Response({"proof_id": proof.id, "status": proof.status})


# --- Xabarlar navbati va jadval ------------------------------------------------

class NotificationsView(BotView):
    def get(self, request):
        limit = min(int(request.query_params.get("limit", 50)), 200)
        items = Notification.objects.filter(sent_at__isnull=True).select_related("user")[:limit]
        return Response([
            {"id": n.id, "telegram_id": n.user.telegram_id, "kind": n.kind, "payload": n.payload}
            for n in items
        ])


class NotificationsAckView(BotView):
    def post(self, request):
        ids = request.data.get("ids") or []
        n = Notification.objects.filter(pk__in=ids, sent_at__isnull=True).update(sent_at=timezone.now())
        return Response({"acked": n})


class AlarmsView(BotView):
    """Bugun shu daqiqada budilnigi chalinishi kerak bo'lganlar (bot har daqiqada so'raydi)."""

    def get(self, request):
        at = parse_time(request.query_params.get("time"), "time")
        today = services.local_now().date()
        result = []
        for m in Membership.objects.filter(
            status=Membership.Status.ACTIVE, cohort__status=Cohort.Status.RUNNING
        ).select_related("cohort", "tribe", "squad", "user"):
            if m.cohort.day_number(today) is None:
                continue
            record = services.ensure_day_record(m, today)
            if record.status == DayRecord.Status.PENDING and record.alarm_time == at.replace(second=0):
                result.append({
                    "telegram_id": m.user.telegram_id,
                    "day_number": record.day_number,
                    "gender": m.tribe.gender,
                    "proof_kind": services.proof_kind(record.day_number),
                    "squad": m.squad.name if m.squad_id else None,
                })
        return Response(result)


class AwardImageView(BotView):
    def get(self, request, pk):
        award = get_object_or_404(Award.objects.select_related("membership__user", "membership__cohort", "stage"), pk=pk)
        return HttpResponse(render_award(award), content_type="image/png")


class CountdownView(BotView):
    """Startni kutayotganlar — bot har kech "Startga N kun qoldi" yuboradi."""

    def get(self, request):
        return Response(services.countdown_list())


class RunDailyView(BotView):
    """Kunlik hisob (bot har kecha 00:05 da va ishga tushganda chaqiradi). Idempotent."""

    def post(self, request):
        call_command("run_daily")
        return Response({"ok": True})
