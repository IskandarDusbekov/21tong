from django.contrib import admin

from .models import Cohort, DayRecord, Freeze, Joker, Membership, Strike, Tribe


class TribeInline(admin.TabularInline):
    model = Tribe
    extra = 0


@admin.register(Cohort)
class CohortAdmin(admin.ModelAdmin):
    list_display = ("name", "start_date", "duration_days", "status")
    list_filter = ("status",)
    inlines = [TribeInline]


@admin.register(Tribe)
class TribeAdmin(admin.ModelAdmin):
    list_display = ("__str__", "cohort", "gender", "telegram_chat_id")
    list_filter = ("cohort", "gender")


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "cohort", "tribe", "target_wake_time", "status", "active_strikes")
    list_filter = ("cohort", "status", "tribe__gender")
    search_fields = ("user__telegram_username", "user__telegram_id")


@admin.register(DayRecord)
class DayRecordAdmin(admin.ModelAdmin):
    list_display = ("membership", "date", "day_number", "alarm_time", "status")
    list_filter = ("status", "date", "membership__cohort")


@admin.register(Strike)
class StrikeAdmin(admin.ModelAdmin):
    list_display = ("membership", "reason", "cancelled_by_joker", "created_at")
    list_filter = ("reason", "cancelled_by_joker")


@admin.register(Joker)
class JokerAdmin(admin.ModelAdmin):
    list_display = ("user", "source", "granted_at", "used_on")
    list_filter = ("source",)


@admin.register(Freeze)
class FreezeAdmin(admin.ModelAdmin):
    list_display = ("membership", "date", "requested_at")
