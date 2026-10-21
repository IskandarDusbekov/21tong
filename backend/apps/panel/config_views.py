"""Sozlamalar, bot matnlari, gaplar, bosqichlar, oqimlar, ommaviy xabar, video raportlar."""
import copy

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import exceptions, serializers
from rest_framework.response import Response

from apps.camp import services
from apps.camp.models import Cohort, Membership, Notification, Squad
from apps.control import defaults
from apps.control.models import SETTINGS_GROUPS, BotMessage, Broadcast, CampSettings, Phrase, Stage
from apps.control.services import broadcast_recipients, send_broadcast
from apps.proofs.models import VideoProof

from .base import PanelView, person


def validation_error(exc: ValidationError):
    if hasattr(exc, "message_dict"):
        return exceptions.ValidationError(exc.message_dict)
    return exceptions.ValidationError({"detail": exc.messages})


# --- Lager sozlamalari ----------------------------------------------------------------

class CampSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampSettings
        exclude = ["id", "updated_at"]

    def validate(self, attrs):
        obj = copy.copy(self.instance) if self.instance else CampSettings()
        for k, v in attrs.items():
            setattr(obj, k, v)
        try:
            obj.clean()
        except ValidationError as e:
            raise serializers.ValidationError({"detail": e.messages})
        return attrs


def field_schema(name):
    f = CampSettings._meta.get_field(name)
    kind = "bool" if isinstance(f, models.BooleanField) else "time" if isinstance(f, models.TimeField) else "int"
    lo = next((v.limit_value for v in f.validators if isinstance(v, MinValueValidator)), None)
    hi = next((v.limit_value for v in f.validators if isinstance(v, MaxValueValidator)), None)
    return {"name": name, "label": str(f.verbose_name), "help": str(f.help_text), "type": kind, "min": lo, "max": hi}


class SettingsView(PanelView):
    def get(self, request):
        c = CampSettings.load()
        return Response({
            "values": CampSettingsSerializer(c).data,
            "groups": [
                {"title": title, "icon": icon, "fields": [field_schema(n) for n in fields]}
                for title, icon, fields in SETTINGS_GROUPS
            ],
            "updated_at": c.updated_at,
        })

    def put(self, request):
        c = CampSettings.objects.get(pk=CampSettings.load().pk)
        s = CampSettingsSerializer(c, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return self.get(request)


# --- Bot xabarlari ----------------------------------------------------------------------

def message_json(m: BotMessage):
    return {
        "key": m.key, "group": m.group, "title": m.title, "text": m.text,
        "default": m.default_text, "changed": m.text != m.default_text,
        "variables": list(defaults.MESSAGES.get(m.key, (None, None, ()))[2]),
        "updated_at": m.updated_at,
    }


class MessagesView(PanelView):
    def get(self, request):
        return Response({
            "items": [message_json(m) for m in BotMessage.objects.all()],
            "settings_vars": CampSettings.load().template_vars(),
        })


class MessageView(PanelView):
    def put(self, request, key):
        m = get_object_or_404(BotMessage, key=key)
        m.text = request.data.get("text", "")
        try:
            m.full_clean()
        except ValidationError as e:
            raise validation_error(e)
        m.save()
        return Response(message_json(m))

    def delete(self, request, key):
        """Standart matnga qaytarish."""
        m = get_object_or_404(BotMessage, key=key)
        m.text = m.default_text
        m.save()
        return Response(message_json(m))


# --- Gaplar va bosqichlar (oddiy CRUD) --------------------------------------------------

class PhraseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Phrase
        fields = ["id", "text", "is_active"]


class StageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stage
        fields = ["id", "day", "name", "description", "icon"]


def crud_views(model, serializer_cls):
    class ListView(PanelView):
        def get(self, request):
            return Response(serializer_cls(model.objects.all(), many=True).data)

        def post(self, request):
            s = serializer_cls(data=request.data)
            s.is_valid(raise_exception=True)
            s.save()
            return Response(s.data, status=201)

    class ItemView(PanelView):
        def patch(self, request, pk):
            s = serializer_cls(get_object_or_404(model, pk=pk), data=request.data, partial=True)
            s.is_valid(raise_exception=True)
            s.save()
            return Response(s.data)

        def delete(self, request, pk):
            get_object_or_404(model, pk=pk).delete()
            return Response(status=204)

    return ListView, ItemView


PhrasesView, PhraseView = crud_views(Phrase, PhraseSerializer)
StagesView, StageView = crud_views(Stage, StageSerializer)


class StageIconsView(PanelView):
    def get(self, request):
        return Response([{"value": v, "label": label} for v, label in Stage.Icon.choices])


# --- Oqimlar -------------------------------------------------------------------------

class CohortSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    end_date = serializers.DateField(read_only=True)

    class Meta:
        model = Cohort
        fields = [
            "id", "name", "start_date", "end_date", "duration_days", "status", "status_label",
            "morning_window_start", "morning_window_end", "evening_window_start", "evening_window_end",
        ]


def cohort_json(c, today):
    data = CohortSerializer(c).data
    members = c.memberships
    data.update({
        "day": c.day_number(today),
        "members": members.count(),
        "active": members.filter(status=Membership.Status.ACTIVE).count(),
        "expelled": members.filter(status=Membership.Status.EXPELLED).count(),
        "squads": Squad.objects.filter(tribe__cohort=c).count(),
    })
    return data


class CohortsView(PanelView):
    def get(self, request):
        today = services.local_now().date()
        return Response({
            "items": [cohort_json(c, today) for c in Cohort.objects.all()],
            "defaults": {
                "duration_days": (s := CampSettings.load()).default_duration_days,
                "morning_window_start": s.default_morning_start.strftime("%H:%M"),
                "morning_window_end": s.default_morning_end.strftime("%H:%M"),
                "evening_window_start": s.default_evening_start.strftime("%H:%M"),
                "evening_window_end": s.default_evening_end.strftime("%H:%M"),
            },
        })

    def post(self, request):
        s = CohortSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        c = s.save()
        return Response(cohort_json(c, services.local_now().date()), status=201)


class CohortView(PanelView):
    def patch(self, request, pk):
        s = CohortSerializer(get_object_or_404(Cohort, pk=pk), data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        c = s.save()
        return Response(cohort_json(c, services.local_now().date()))


class CohortActionView(PanelView):
    def post(self, request, pk):
        c = get_object_or_404(Cohort, pk=pk)
        action = request.data.get("action")
        if action == "open":
            c.status = Cohort.Status.RECRUITING
            msg = "Qabul ochildi — yangi qabul qilinganlar shu oqimga tushadi."
        elif action == "start":
            c.status = Cohort.Status.RUNNING
            msg = "Oqim boshlandi."
        elif action == "finish":
            c.status = Cohort.Status.FINISHED
            c.memberships.filter(status=Membership.Status.ACTIVE).update(status=Membership.Status.FINISHED)
            msg = "Oqim yakunlandi."
        elif action == "run_daily":
            call_command("run_daily")
            return Response({"detail": "Kunlik hisob bajarildi: kechagi kunlar baholandi, bugungi kunlar ochildi."})
        else:
            raise exceptions.ValidationError({"detail": "Noma'lum amal."})
        c.save(update_fields=["status"])
        return Response({"detail": msg})


# --- Ommaviy xabar ---------------------------------------------------------------------

class BroadcastSerializer(serializers.ModelSerializer):
    audience_label = serializers.CharField(source="get_audience_display", read_only=True)

    class Meta:
        model = Broadcast
        fields = ["id", "text", "audience", "audience_label", "cohort", "squad", "gender", "created_at", "sent_count"]
        read_only_fields = ["created_at", "sent_count"]

    def validate(self, attrs):
        try:
            Broadcast(**attrs).clean()
        except ValidationError as e:
            raise serializers.ValidationError(e.message_dict)
        return attrs


class BroadcastsView(PanelView):
    def get(self, request):
        return Response({
            "items": BroadcastSerializer(Broadcast.objects.all()[:50], many=True).data,
            "audiences": [{"value": v, "label": label} for v, label in Broadcast.Audience.choices],
            "cohorts": [{"id": c.id, "name": c.name} for c in Cohort.objects.exclude(status=Cohort.Status.FINISHED)],
            "squads": [
                {"id": s.id, "name": str(s)}
                for s in Squad.objects.exclude(tribe__cohort__status=Cohort.Status.FINISHED).select_related("tribe")
            ],
        })

    def post(self, request):
        s = BroadcastSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        if request.query_params.get("preview"):
            return Response({"recipients": broadcast_recipients(Broadcast(**s.validated_data)).count()})
        b = s.save()
        n = send_broadcast(b)
        return Response({**BroadcastSerializer(b).data, "detail": f"Xabar {n} kishiga yuborilmoqda."}, status=201)


# --- Video raportlar ---------------------------------------------------------------------

class VideosView(PanelView):
    def get(self, request):
        status = request.query_params.get("status", VideoProof.Status.REVIEWING)
        qs = VideoProof.objects.select_related("day__membership__user", "day__membership__squad").order_by("-uploaded_at")
        if status != "all":
            qs = qs.filter(status=status)
        return Response([
            {
                "id": v.id, "user": person(v.day.membership.user), "membership_id": v.day.membership_id,
                "squad": v.day.membership.squad.name if v.day.membership.squad_id else None,
                "day": v.day.day_number, "phrase": v.day.phrase, "status": v.status,
                "status_label": v.get_status_display(), "uploaded_at": v.uploaded_at,
                "votes": list(v.reviews.values_list("approved", flat=True)),
            }
            for v in qs[:200]
        ])


class VideoDecisionView(PanelView):
    def post(self, request, pk, decision):
        v = get_object_or_404(VideoProof.objects.select_related("day__membership__user"), pk=pk)
        approved = decision == "approve"
        v.status = VideoProof.Status.APPROVED if approved else VideoProof.Status.REJECTED
        v.decided_at = timezone.now()
        v.save(update_fields=["status", "decided_at"])
        kind = Notification.Kind.VIDEO_APPROVED if approved else Notification.Kind.VIDEO_REJECTED
        services.notify(v.day.membership.user, kind, day_number=v.day.day_number)
        return Response({"detail": "Video tasdiqlandi." if approved else "Video rad etildi."})

