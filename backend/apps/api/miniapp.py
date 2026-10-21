"""Telegram Mini App API. Foydalanuvchi initData (yoki lokal dev kirish) orqali aniqlanadi."""
from django.conf import settings
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import exceptions
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.auth import DevAuthentication, TelegramInitDataAuthentication
from apps.accounts.models import User
from apps.camp import rules, services
from apps.community import services as community
from apps.community.models import Bounty, Reflection

from .common import membership_summary


class AppView(APIView):
    authentication_classes = [TelegramInitDataAuthentication, DevAuthentication]
    permission_classes = [IsAuthenticated]

    def membership(self):
        m = services.active_membership(self.request.user)
        if m is None:
            raise exceptions.PermissionDenied("Siz hozir faol oqimda emassiz.")
        return m


class MeView(AppView):
    def get(self, request):
        user = request.user
        m = services.active_membership(user)
        today = None
        stage = None
        if m is not None:
            now = services.local_now()
            if m.cohort.day_number(now.date()):
                today = services.day_progress(services.ensure_day_record(m, now.date()))
            survived = m.days.exclude(status__in=["pending", "failed"]).count()
            stage = rules.stage_for(survived)
        return Response({
            "first_name": user.first_name,
            "gender": user.gender,
            "status": user.status,
            "jokers": services.jokers_available(user),
            "coins": community.coin_balance(user),
            "membership": membership_summary(m),
            "today": today,
            "stage": stage,
            "max_strikes": rules.MAX_STRIKES,
        })


class WakeView(AppView):
    def post(self, request):
        record = services.press_wake(self.membership())
        return Response(services.day_progress(record))


class FreezeView(AppView):
    def post(self, request):
        freeze = services.request_freeze(self.membership(), request.data.get("reason", ""))
        return Response({"date": freeze.date}, status=201)


class FeedView(AppView):
    def get(self, request):
        m = self.membership()
        items = community.feed(m, services.local_now().date())
        return Response([
            {
                "id": r.id,
                "author": r.membership.user.first_name or "Ishtirokchi",
                "text": r.text,
                "fires": r.fire_count,
                "fired_by_me": bool(r.fired_by_me),
                "mine": r.membership_id == m.id,
            }
            for r in items
        ])

    def post(self, request):
        r = community.add_reflection(self.membership(), request.data.get("text", ""))
        return Response({"id": r.id, "text": r.text}, status=201)


class FireView(AppView):
    def post(self, request, pk):
        community.give_fire(self.membership(), get_object_or_404(Reflection, pk=pk))
        return Response({"ok": True})


class BountiesView(AppView):
    def get(self, request):
        m = self.membership()
        done = set(m.bounty_completions.values_list("bounty_id", flat=True))
        bounties = Bounty.objects.filter(cohort=m.cohort, date=services.local_now().date())
        return Response([
            {"id": b.id, "title": b.title, "description": b.description, "reward": b.reward, "done": b.id in done}
            for b in bounties
        ])


class BountyCompleteView(AppView):
    def post(self, request, pk):
        m = self.membership()
        community.complete_bounty(m, get_object_or_404(Bounty, pk=pk), request.data.get("note", ""))
        return Response({"coins": community.coin_balance(m.user)}, status=201)


class DevUsersView(APIView):
    """Dev kirish ekrani uchun foydalanuvchilar ro'yxati. Faqat DEV_LOGIN yoqilganda."""

    def get(self, request):
        if not settings.DEV_LOGIN:
            raise Http404
        users = User.objects.filter(telegram_id__isnull=False).order_by("gender", "first_name")
        return Response([
            {
                "telegram_id": u.telegram_id,
                "name": u.first_name or u.username,
                "gender": u.gender,
                "status": u.status,
            }
            for u in users
        ])


class LeaderboardView(AppView):
    def get(self, request):
        m = self.membership()
        return Response([
            {"name": x.user.first_name or "Ishtirokchi", "coins": x.coins, "me": x.id == m.id}
            for x in community.leaderboard(m)
        ])
