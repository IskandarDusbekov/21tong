from django.contrib import admin
from django.core.management import call_command
from django.db.models import Count, Q
from django.utils.html import format_html

from apps.control.models import CampSettings

from . import services
from .models import Cohort, DayRecord, Freeze, Immunity, Membership, Notification, Squad, Strike, Tribe


# --- Oqim ------------------------------------------------------------------------

class TribeInline(admin.TabularInline):
    model = Tribe
    extra = 0
    show_change_link = True


@admin.register(Cohort)
class CohortAdmin(admin.ModelAdmin):
    list_display = ("name", "start_date", "end_date", "status", "progress", "members_count")
    list_filter = ("status",)
    inlines = [TribeInline]
    actions = ["open_recruiting", "start", "finish", "run_daily_now"]
    fieldsets = (
        (None, {"fields": ("name", "start_date", "duration_days", "status")}),
        ("Chat oynalari", {"fields": (
            ("morning_window_start", "morning_window_end"), ("evening_window_start", "evening_window_end"),
        )}),
    )

    def get_changeform_initial_data(self, request):
        c = CampSettings.load()
        return {
            "duration_days": c.default_duration_days,
            "morning_window_start": c.default_morning_start, "morning_window_end": c.default_morning_end,
            "evening_window_start": c.default_evening_start, "evening_window_end": c.default_evening_end,
        }

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            n_active=Count("memberships", filter=Q(memberships__status=Membership.Status.ACTIVE))
        )

    @admin.display(description="Tugash sanasi")
    def end_date(self, obj):
        return obj.end_date

    @admin.display(description="Kun")
    def progress(self, obj):
        day = obj.day_number(services.local_now().date())
        return f"{day}/{obj.duration_days}" if day else "—"

    @admin.display(description="Faol", ordering="n_active")
    def members_count(self, obj):
        return obj.n_active

    @admin.action(description="Qabulni ochish")
    def open_recruiting(self, request, queryset):
        n = queryset.update(status=Cohort.Status.RECRUITING)
        self.message_user(request, f"{n} ta oqimda qabul ochildi — yangi tasdiqlanganlar shu oqimga tushadi.")

    @admin.action(description="Oqimni boshlash (hozir)")
    def start(self, request, queryset):
        n = queryset.update(status=Cohort.Status.RUNNING)
        self.message_user(request, f"{n} ta oqim boshlandi.")

    @admin.action(description="Oqimni yakunlash")
    def finish(self, request, queryset):
        for c in queryset:
            c.status = Cohort.Status.FINISHED
            c.save(update_fields=["status"])
            c.memberships.filter(status=Membership.Status.ACTIVE).update(status=Membership.Status.FINISHED)
        self.message_user(request, f"{queryset.count()} ta oqim yakunlandi.")

    @admin.action(description="Kunlik jarayonni hozir ishga tushirish (kechagi kunni baholash)")
    def run_daily_now(self, request, queryset):
        call_command("run_daily")
        self.message_user(request, "Kunlik jarayon bajarildi: kechagi kunlar baholandi, bugungi kunlar ochildi.")


@admin.register(Tribe)
class TribeAdmin(admin.ModelAdmin):
    list_display = ("__str__", "cohort", "gender", "squads_count")
    list_filter = ("cohort", "gender")

    @admin.display(description="Rotalar")
    def squads_count(self, obj):
        return obj.squads.count()

    def get_inlines(self, request, obj):
        return [SquadInline]


class SquadInline(admin.TabularInline):
    model = Squad
    extra = 0
    show_change_link = True


# --- Rota --------------------------------------------------------------------------

class MemberInline(admin.TabularInline):
    model = Membership
    fk_name = "squad"
    fields = ("user", "status", "target_wake_time", "strikes")
    readonly_fields = ("user", "strikes")
    extra = 0
    can_delete = False
    show_change_link = True

    @admin.display(description="Ogohlantirish")
    def strikes(self, obj):
        return obj.active_strikes

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Squad)
class SquadAdmin(admin.ModelAdmin):
    list_display = ("__str__", "members_count", "chat_status", "invite_link")
    list_filter = ("tribe__cohort", "tribe__gender")
    inlines = [MemberInline]

    @admin.display(description="A'zolar")
    def members_count(self, obj):
        return obj.memberships.filter(status=Membership.Status.ACTIVE).count()

    @admin.display(description="Guruh")
    def chat_status(self, obj):
        if obj.telegram_chat_id:
            return format_html('<span style="color:#16a34a">{}</span>', "✔ ulangan")
        return format_html('<span style="color:#d97706">{}</span>', "ulanmagan — guruhda /ulash")


# --- Ishtirokchi ----------------------------------------------------------------------

class StrikeInline(admin.TabularInline):
    model = Strike
    fields = ("reason", "day", "cancelled_by_immunity", "revoked", "created_at")
    readonly_fields = ("reason", "day", "cancelled_by_immunity", "created_at")
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class DayInline(admin.TabularInline):
    model = DayRecord
    fields = ("day_number", "date", "alarm_time", "woke_at", "voice_at", "status")
    readonly_fields = fields
    extra = 0
    can_delete = False
    ordering = ("-date",)

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "cohort", "tribe", "squad", "target_wake_time", "status", "strikes", "immunities")
    list_filter = ("cohort", "status", "tribe__gender", "squad")
    search_fields = ("user__first_name", "user__telegram_username", "user__telegram_id")
    list_select_related = ("user", "cohort", "tribe", "squad")
    raw_id_fields = ("user",)
    inlines = [StrikeInline, DayInline]
    actions = ["give_immunity", "give_strike", "revoke_last_strike", "expel", "restore", "make_mentor"]

    @admin.display(description="Ogohlantirish")
    def strikes(self, obj):
        return f"{obj.active_strikes}/{CampSettings.load().max_strikes}"

    @admin.display(description="Immunitet")
    def immunities(self, obj):
        return services.immunities_available(obj.user)

    @admin.action(description="Immunitet berish (+1)")
    def give_immunity(self, request, queryset):
        for m in queryset:
            services.grant_immunity(m.user, Immunity.Source.ADMIN)
        self.message_user(request, f"{queryset.count()} kishiga Immunitet berildi.")

    @admin.action(description="Ogohlantirish berish (qo'mondonlik qarori)")
    def give_strike(self, request, queryset):
        expelled = sum(
            services.issue_strike(m, Strike.Reason.ADMIN, use_immunity=False).expelled
            for m in queryset.filter(status=Membership.Status.ACTIVE)
        )
        self.message_user(request, f"Ogohlantirish berildi. Chiqarildi: {expelled}.")

    @admin.action(description="Oxirgi ogohlantirishni bekor qilish")
    def revoke_last_strike(self, request, queryset):
        n = 0
        for m in queryset:
            last = m.strikes.filter(revoked=False, cancelled_by_immunity=False).order_by("-created_at").first()
            if last:
                services.revoke_strike(last)
                n += 1
        self.message_user(request, f"{n} ta ogohlantirish bekor qilindi.")

    @admin.action(description="Lagerdan chiqarish")
    def expel(self, request, queryset):
        for m in queryset.filter(status=Membership.Status.ACTIVE):
            services.expel(m)
        self.message_user(request, "Tanlanganlar lagerdan chiqarildi.")

    @admin.action(description="Lagerga qaytarish (faol qilish)")
    def restore(self, request, queryset):
        for m in queryset:
            services.restore(m)
        self.message_user(request, f"{queryset.count()} kishi faol holatga qaytarildi.")

    @admin.action(description="Mentor qilish")
    def make_mentor(self, request, queryset):
        n = queryset.update(status=Membership.Status.MENTOR)
        self.message_user(request, f"{n} kishi Mentor bo'ldi.")


# --- Kunlik yozuvlar ---------------------------------------------------------------

@admin.register(DayRecord)
class DayRecordAdmin(admin.ModelAdmin):
    list_display = ("membership", "day_number", "date", "alarm_time", "woke_at", "voice_at", "video_status", "status")
    list_filter = ("status", "date", "membership__cohort", "membership__squad")
    search_fields = ("membership__user__first_name", "membership__user__telegram_username")
    list_select_related = ("membership__user", "video")
    date_hierarchy = "date"
    readonly_fields = ("membership", "date", "day_number", "phrase", "woke_at", "voice_at", "voice_file_id", "evaluated_at")
    actions = ["excuse", "evaluate_now"]

    @admin.display(description="Video")
    def video_status(self, obj):
        video = getattr(obj, "video", None)
        return video.get_status_display() if video else "—"

    @admin.action(description="Uzrli deb belgilash (bajarildi + ogohlantirishni bekor qilish)")
    def excuse(self, request, queryset):
        for r in queryset:
            services.excuse_day(r)
        self.message_user(request, f"{queryset.count()} ta kun uzrli deb belgilandi.")

    @admin.action(description="Hozir baholash")
    def evaluate_now(self, request, queryset):
        for r in queryset.filter(status=DayRecord.Status.PENDING):
            services.evaluate_day(r)
        self.message_user(request, "Baholandi.")


@admin.register(Strike)
class StrikeAdmin(admin.ModelAdmin):
    list_display = ("membership", "reason", "day", "cancelled_by_immunity", "revoked", "created_at")
    list_filter = ("reason", "cancelled_by_immunity", "revoked", "membership__cohort")
    search_fields = ("membership__user__first_name", "membership__user__telegram_username")
    list_select_related = ("membership__user", "day")
    actions = ["revoke"]

    def has_add_permission(self, request):
        return False  # ogohlantirish "Ishtirokchilar" bo'limidagi amal orqali beriladi

    @admin.action(description="Bekor qilish")
    def revoke(self, request, queryset):
        for s in queryset:
            services.revoke_strike(s)
        self.message_user(request, f"{queryset.count()} ta ogohlantirish bekor qilindi.")


@admin.register(Immunity)
class ImmunityAdmin(admin.ModelAdmin):
    list_display = ("user", "source", "granted_at", "used_on")
    list_filter = ("source",)
    search_fields = ("user__first_name", "user__telegram_username")
    raw_id_fields = ("user", "used_on")


@admin.register(Freeze)
class FreezeAdmin(admin.ModelAdmin):
    list_display = ("membership", "date", "reason", "requested_at")
    list_filter = ("date",)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "kind", "created_at", "sent_at")
    list_filter = ("kind", ("sent_at", admin.EmptyFieldListFilter))
    search_fields = ("user__first_name", "user__telegram_username")
    readonly_fields = ("user", "kind", "payload", "created_at", "sent_at")

    def has_add_permission(self, request):
        return False
