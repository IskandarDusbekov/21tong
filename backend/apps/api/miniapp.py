"""Telegram Mini App API. Foydalanuvchi initData (yoki lokal dev kirish) orqali aniqlanadi."""
import logging

import httpx
from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import exceptions
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.auth import DevAuthentication, TelegramInitDataAuthentication
from apps.accounts.models import User
from apps.camp import rules, services
from apps.camp.awards import render_award
from apps.camp.models import Award, DayRecord
from apps.community import services as community
from apps.community.models import Bounty, PhotoEntry, Reflection
from apps.proofs import services as proofs_services
from apps.proofs.models import Review, VideoProof

from .common import membership_summary

log = logging.getLogger(__name__)


class AppView(APIView):
    authentication_classes = [TelegramInitDataAuthentication, DevAuthentication]
    permission_classes = [IsAuthenticated]

    def membership(self):
        m = services.active_membership(self.request.user)
        if m is None:
            raise exceptions.PermissionDenied("Siz hozir faol oqimda emassiz.")
        return m

    def chat_membership(self):
        """Chat uchun — oqim boshlangan bo'lsa ham, hali boshlanmagan (start kutayotgan) bo'lsa ham."""
        m = services.active_membership(self.request.user) or services.upcoming_membership(self.request.user)
        if m is None:
            raise exceptions.PermissionDenied("Siz hozir faol oqimda emassiz.")
        return m


class MeView(AppView):
    def get(self, request):
        user = request.user
        m = services.active_membership(user)
        today = None
        journey = None
        if m is not None:
            now = services.local_now()
            if m.cohort.day_number(now.date()):
                today = services.day_progress(services.ensure_day_record(m, now.date()))
            journey = services.journey(m, now)
        upcoming = services.upcoming_membership(user) if m is None else None
        awards = Award.objects.filter(membership__user=user).select_related("stage").order_by("stage__day")
        return Response({
            "first_name": user.first_name,
            "full_name": user.display_name,
            "profile": {
                "region": user.get_region_display() if user.region else "",
                "username": user.telegram_username,
                "joined": user.approved_at.date().isoformat() if user.approved_at else None,
                "referral_code": user.referral_code,
                "standing": community.standing(m) if m is not None else None,
            },
            "upcoming": {
                **services.placement_payload(upcoming),
                "rules": {"wake_grace": rules.current().wake_grace_minutes, "voice_deadline": rules.current().voice_deadline_minutes},
            } if upcoming else None,
            "awards": [services.award_json(a) for a in awards],
            "gender": user.gender,
            "status": user.status,
            "goal": user.goal,
            "immunities": services.immunities_available(user),
            "coins": community.coin_balance(user),
            "membership": membership_summary(m),
            "today": today,
            "journey": journey,
            "stage": journey["stage"] if journey else None,
            "max_strikes": rules.current().max_strikes,
            "reflection_max_length": rules.current().reflection_max_length,
        })


class WakeView(AppView):
    def post(self, request):
        record = services.press_wake(self.membership())
        return Response(services.day_progress(record))


class SquadView(AppView):
    """Rota va bugungi raport — kim turdi, kim yo'q."""

    def get(self, request):
        m = self.membership()
        if not m.squad_id:
            return Response(None)
        report = services.squad_report(m.squad, services.local_now().date())
        for row in report["members"]:
            row["me"] = row.pop("telegram_id") == request.user.telegram_id
            row.pop("membership_id")
        return Response(report)


class ChatView(AppView):
    """Rota chati: raportlar, ogohlantirishlar, bosqichlar va matn xabarlari (Telegram guruh o'rniga)."""

    def get(self, request):
        return Response(community.squad_chat(self.chat_membership()))

    def post(self, request):
        msg = community.post_chat_message(self.chat_membership(), request.data.get("text", ""))
        return Response({"id": msg.id, "text": msg.text}, status=201)


def _stream_telegram_file(file_id, content_type):
    """Raport media'sini (ovoz/video) Telegram'dan olib qaytaradi — ilovada eshitiladi/ko'riladi.
    Fayllar kichik (ovoz ~100KB, video krujok bir necha MB) — to'liq yuklab beramiz: oqim'ga
    nisbatan ancha ishonchli (gunicorn ostida ham to'g'ri ishlaydi)."""
    token = settings.TELEGRAM_BOT_TOKEN
    if not token or not file_id or file_id.startswith("demo-"):
        raise Http404
    base = f"https://api.telegram.org/bot{token}"
    try:
        info = httpx.get(f"{base}/getFile", params={"file_id": file_id}, timeout=20).json()
        if not info.get("ok"):
            log.warning("getFile muvaffaqiyatsiz: %s", info.get("description"))
            raise Http404
        path = info["result"]["file_path"]
        r = httpx.get(f"https://api.telegram.org/file/bot{token}/{path}", timeout=60)
        r.raise_for_status()
    except (httpx.HTTPError, KeyError, TypeError) as e:
        log.warning("Telegram fayl olinmadi (%s): %s", file_id[:12], e)
        raise Http404
    resp = HttpResponse(r.content, content_type=r.headers.get("content-type", content_type))
    resp["Cache-Control"] = "private, max-age=86400"
    return resp


class ProofMediaView(AppView):
    """Faqat o'z rotasidagi raportning ovozi/videosi."""

    def get(self, request, kind, pk):
        m = self.membership()
        if kind == "voice":
            record = get_object_or_404(DayRecord, pk=pk, membership__squad=m.squad_id)
            return _stream_telegram_file(record.voice_file_id, "audio/ogg")
        if kind == "water":  # iliq suv rasmi — Mini App'da yuklangan
            record = get_object_or_404(DayRecord, pk=pk, membership__squad=m.squad_id, water_photo__gt="")
            return FileResponse(record.water_photo.open("rb"), content_type="image/jpeg")
        if kind == "video":
            proof = get_object_or_404(VideoProof, pk=pk, day__membership__squad=m.squad_id)
            if proof.file:  # Mini App ichida yozilgan — lokal fayl
                ctype = "video/webm" if proof.file.name.endswith(".webm") else "video/mp4"
                return FileResponse(proof.file.open("rb"), content_type=ctype)
            return _stream_telegram_file(proof.telegram_file_id, "video/mp4")
        raise Http404


class VideoVoteView(AppView):
    """Rotadosh yurish videosini ilova ichida tasdiqlaydi/rad etadi (bot o'rniga)."""

    def post(self, request, pk):
        m = self.membership()
        proof = get_object_or_404(VideoProof, pk=pk, day__membership__squad=m.squad_id)
        review = get_object_or_404(Review, proof=proof, reviewer=m)
        proof = proofs_services.cast_vote(review, m, bool(request.data.get("approved")))
        return Response({"status": proof.status})


class WaterUploadView(AppView):
    """2-topshiriq: iliq suv ichilgani rasmi (multipart: photo)."""

    def post(self, request):
        upload = request.FILES.get("photo")
        if not upload:
            raise exceptions.ValidationError("Rasm topilmadi.")
        if upload.size > 10 * 1024 * 1024:
            raise exceptions.ValidationError("Rasm juda katta (maksimal 10 MB).")
        try:  # haqiqiy rasm ekanini tekshiramiz
            from PIL import Image
            Image.open(upload).verify()
            upload.seek(0)
        except Exception:
            raise exceptions.ValidationError("Bu rasm fayli emas.")
        record = services.record_water(self.membership(), upload)
        return Response(services.day_progress(record), status=201)


class VideoUploadView(AppView):
    """Mini App ichida kameradan yozilgan video raportni qabul qiladi (multipart: video + duration)."""

    def post(self, request):
        upload = request.FILES.get("video")
        if not upload:
            raise exceptions.ValidationError("Video fayl topilmadi.")
        if upload.size > 25 * 1024 * 1024:
            raise exceptions.ValidationError("Video juda katta (maksimal 25 MB).")
        try:
            duration = max(0, min(int(request.data.get("duration") or 0), 60))
        except (TypeError, ValueError):
            duration = 0
        proof = proofs_services.submit_video_file(self.membership(), upload, duration)
        return Response({"proof_status": proof.status, "day_number": proof.day.day_number}, status=201)


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


class AwardImageView(AppView):
    """Faqat o'z mukofotining rasmi."""

    def get(self, request, pk):
        award = get_object_or_404(
            Award.objects.select_related("membership__user", "membership__cohort", "stage"),
            pk=pk, membership__user=request.user,
        )
        return HttpResponse(render_award(award), content_type="image/png")


class LeaderboardView(AppView):
    """Ko'p bosqichli reyting: rota ichida, rotalar o'rtasida, qabila eng zo'rlari."""

    def get(self, request):
        return Response(community.ranking(self.membership()))


class PhotosView(AppView):
    """Tonggi rasm chelenji: o'z qabilasidagi rasmlar va yangisini yuklash."""

    def get(self, request):
        return Response(community.photo_feed(self.membership()))

    def post(self, request):
        entry = community.upload_photo(self.membership(), request.FILES.get("image"))
        return Response({"id": entry.id}, status=201)


class PhotoVoteView(AppView):
    def post(self, request, pk):
        m = self.membership()
        entry = get_object_or_404(PhotoEntry, pk=pk)
        voted = community.vote_photo(m, entry)
        return Response({"voted": voted})


class PhotoImageView(AppView):
    """Faqat o'z qabilasidagi (bir jinsdagi) rasmni ko'rsatadi."""

    def get(self, request, pk):
        m = self.membership()
        entry = get_object_or_404(
            PhotoEntry.objects.select_related("membership__tribe", "challenge"),
            pk=pk, challenge__cohort_id=m.cohort_id, membership__tribe__gender=m.tribe.gender,
        )
        try:
            return FileResponse(entry.image.open("rb"), content_type="image/jpeg")
        except FileNotFoundError:
            raise Http404
