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

from django.http import HttpResponse

from apps.accounts.models import User
from apps.camp import services
from apps.camp.awards import render_award, render_preview
from apps.camp.models import Award, Cohort, Membership, Notification, Squad, WakeSlot
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
        fields = ["id", "day", "name", "description", "icon", "award_type", "rank", "stars"]


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
        return Response({
            "icons": [{"value": v, "label": label} for v, label in Stage.Icon.choices],
            "award_types": [{"value": v, "label": label} for v, label in Stage.AwardType.choices],
        })


class StagePreviewView(PanelView):
    """Bosqich mukofotining namunaviy rasmi (panelda <img> orqali ko'rsatiladi)."""

    def get(self, request, pk):
        return HttpResponse(render_preview(get_object_or_404(Stage, pk=pk)), content_type="image/png")


class AwardImageView(PanelView):
    def get(self, request, pk):
        award = get_object_or_404(Award.objects.select_related("membership__user", "membership__cohort", "stage"), pk=pk)
        return HttpResponse(render_award(award), content_type="image/png")


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


class SlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = WakeSlot
        fields = ["id", "start_wake_time", "target_wake_time", "title", "is_open"]

    def validate(self, attrs):
        start = attrs.get("start_wake_time", getattr(self.instance, "start_wake_time", None))
        target = attrs.get("target_wake_time", getattr(self.instance, "target_wake_time", None))
        if start and target and target > start:
            raise serializers.ValidationError({"detail": "Maqsad vaqti boshlang'ich vaqtdan erta bo'lishi kerak."})
        return attrs


def slot_row(s):
    data = SlotSerializer(s).data
    data["start_wake_time"], data["target_wake_time"] = data["start_wake_time"][:5], data["target_wake_time"][:5]
    data["members"] = Membership.objects.filter(
        cohort=s.cohort, tribe__start_wake_time=s.start_wake_time, target_wake_time=s.target_wake_time
    ).count()
    data["pending"] = s.applicants.filter(status="pending").count()
    return data


def cohort_json(c, today):
    data = CohortSerializer(c).data
    members = c.memberships
    data["slots"] = [slot_row(s) for s in c.slots.all()]
    data["days_left"] = services.days_until(c.start_date, today)
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
    def delete(self, request, pk):
        """Xato yaratilgan oqimni o'chirish — faqat hali hech kim qo'shilmagan bo'lsa."""
        c = get_object_or_404(Cohort, pk=pk)
        if c.memberships.exists():
            raise exceptions.ValidationError({"detail": "Oqimda ishtirokchilar bor — o'chirib bo'lmaydi. Uni «Yakunlash» mumkin."})
        if User.objects.filter(preferred_slot__cohort=c, status=User.Status.PENDING).exists():
            raise exceptions.ValidationError({"detail": "Bu oqimga ariza berganlar bor — avval arizalarni hal qiling."})
        c.delete()
        return Response(status=204)

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
            # Qo'lda "start" — oqim BUGUNDAN boshlanadi (1-kun bugun), start sanasi qanday
            # bo'lishidan qat'i nazar. Shunda "oxirgi kun" kabi xato kun raqami chiqmaydi.
            c.status = Cohort.Status.RUNNING
            c.start_date = services.local_now().date()
            msg = "Oqim boshlandi — bugun 1-kun."
        elif action == "finish":
            c.status = Cohort.Status.FINISHED
            c.memberships.filter(status=Membership.Status.ACTIVE).update(status=Membership.Status.FINISHED)
            msg = "Oqim yakunlandi."
        elif action == "clone_next":
            days = int(request.data.get("days") or 7)
            new = services.clone_cohort(c, days)
            return Response({"detail": f"Keyingi oqim ochildi: {new.name} (start {new.start_date:%d.%m.%Y}). Qabulni ochishni unutmang.", "id": new.id})
        elif action == "run_daily":
            call_command("run_daily")
            return Response({"detail": "Kunlik hisob bajarildi: kechagi kunlar baholandi, bugungi kunlar ochildi."})
        else:
            raise exceptions.ValidationError({"detail": "Noma'lum amal."})
        c.save()
        return Response({"detail": msg})


class SlotsView(PanelView):
    def post(self, request, pk):
        cohort = get_object_or_404(Cohort, pk=pk)
        s = SlotSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        if WakeSlot.objects.filter(cohort=cohort, start_wake_time=s.validated_data["start_wake_time"],
                                   target_wake_time=s.validated_data["target_wake_time"]).exists():
            raise exceptions.ValidationError({"detail": "Bunday rota vaqti allaqachon bor."})
        return Response(slot_row(s.save(cohort=cohort)), status=201)


class SlotView(PanelView):
    def patch(self, request, pk):
        slot = get_object_or_404(WakeSlot, pk=pk)
        s = SlotSerializer(slot, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        time_changed = (d.get("start_wake_time", slot.start_wake_time) != slot.start_wake_time
                        or d.get("target_wake_time", slot.target_wake_time) != slot.target_wake_time)
        if time_changed and slot_row(slot)["members"]:
            raise exceptions.ValidationError({"detail": (
                "Bu rotaga odamlar joylashgan — vaqtini o'zgartirib bo'lmaydi. "
                "Nomini o'zgartirish yoki tanlashni yopish mumkin."
            )})
        return Response(slot_row(s.save()))

    def delete(self, request, pk):
        get_object_or_404(WakeSlot, pk=pk).delete()
        return Response(status=204)


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
        if approved:
            services.award_task(v.day, "video")
        kind = Notification.Kind.VIDEO_APPROVED if approved else Notification.Kind.VIDEO_REJECTED
        services.notify(v.day.membership.user, kind, day_number=v.day.day_number)
        return Response({"detail": "Video tasdiqlandi." if approved else "Video rad etildi."})

