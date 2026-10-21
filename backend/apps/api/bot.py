"""Bot -> backend API. Hammasi `X-Bot-Secret` bilan himoyalangan."""
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.auth import IsBot
from apps.accounts.manifest import render_manifest
from apps.accounts.models import User
from apps.camp import services
from apps.camp.models import Cohort, DayRecord, Membership, Notification, Tribe
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
    membership = user.memberships.select_related("cohort", "tribe").order_by("-joined_at").first()
    return {
        "telegram_id": user.telegram_id,
        "status": user.status,
        "gender": user.gender,
        "goal": user.goal,
        "referral_code": user.referral_code,
        "jokers": services.jokers_available(user),
        "membership": membership_summary(membership),
    }


class RegisterView(BotView):
    def post(self, request):
        telegram_id, gender, goal = require(request.data, "telegram_id", "gender", "goal")
        user = services.register_user(
            telegram_id=int(telegram_id), gender=gender, goal=goal,
            username=request.data.get("username", ""),
            first_name=request.data.get("first_name", ""),
            referral_code=request.data.get("referral_code"),
        )
        return Response(user_payload(user), status=201)


class UserView(BotView):
    def get(self, request, telegram_id):
        return Response(user_payload(self.get_user(telegram_id)))


class ManifestView(BotView):
    def get(self, request, telegram_id):
        user = self.get_user(telegram_id)
        if not user.goal:
            raise exceptions.ValidationError({"detail": "Maqsad hali yozilmagan."})
        return HttpResponse(render_manifest(user), content_type="image/png")


class RecruitingCohortsView(BotView):
    def get(self, request):
        cohorts = Cohort.objects.filter(status=Cohort.Status.RECRUITING).order_by("start_date")
        return Response([{"id": c.id, "name": c.name, "start_date": c.start_date} for c in cohorts])


class JoinView(BotView):
    def post(self, request):
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


class VoiceView(BotView):
    """Bot qabila guruhida voice ko'rganda chaqiradi."""

    def post(self, request):
        telegram_id, chat_id = require(request.data, "telegram_id", "chat_id")
        membership = self.get_active(telegram_id)
        if membership.tribe.telegram_chat_id != int(chat_id):
            raise exceptions.ValidationError({"detail": "Ovozli xabar o'z qabilangiz guruhiga yuborilishi kerak."})
        record = services.record_voice(membership)
        return Response(services.day_progress(record))


class VideoView(BotView):
    def post(self, request):
        telegram_id, file_id = require(request.data, "telegram_id", "file_id")
        membership = self.get_active(telegram_id)
        proof = proof_services.submit_video(membership, file_id, int(request.data.get("duration") or 0))
        return Response({"proof_id": proof.id, "status": proof.status}, status=201)


class VoteView(BotView):
    def post(self, request, review_id):
        telegram_id, approved = require(request.data, "telegram_id", "approved")
        review = get_object_or_404(Review, pk=review_id)
        voter = get_object_or_404(Membership, user__telegram_id=telegram_id, pk=review.reviewer_id)
        proof = proof_services.cast_vote(review, voter, bool(approved))
        return Response({"proof_id": proof.id, "status": proof.status})


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
        ).select_related("cohort", "tribe", "user"):
            if m.cohort.day_number(today) is None:
                continue
            record = services.ensure_day_record(m, today)
            if record.status == DayRecord.Status.PENDING and record.alarm_time == at.replace(second=0):
                result.append({
                    "telegram_id": m.user.telegram_id,
                    "day_number": record.day_number,
                    "gender": m.tribe.gender,
                })
        return Response(result)


class WindowsView(BotView):
    """Qabila chatlari va ularning ochiq oynalari — bot chatlarni qulflash/ochish uchun."""

    def get(self, request):
        tribes = Tribe.objects.filter(
            cohort__status=Cohort.Status.RUNNING, telegram_chat_id__isnull=False
        ).select_related("cohort")
        return Response([
            {
                "chat_id": t.telegram_chat_id,
                "gender": t.gender,
                "morning": [t.cohort.morning_window_start.strftime("%H:%M"), t.cohort.morning_window_end.strftime("%H:%M")],
                "evening": [t.cohort.evening_window_start.strftime("%H:%M"), t.cohort.evening_window_end.strftime("%H:%M")],
            }
            for t in tribes
        ])
