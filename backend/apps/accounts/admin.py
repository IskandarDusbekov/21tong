from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.camp import services
from apps.camp.models import Immunity

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("__str__", "first_name", "last_name", "region", "gender", "status", "wake_times", "short_goal", "date_joined")
    list_filter = ("status", "gender", "region", "is_staff")
    search_fields = ("username", "first_name", "telegram_username", "telegram_id", "goal")
    actions = ["approve", "reject", "give_immunity"]
    fieldsets = (
        ("Ariza", {"fields": (
            "first_name", "last_name", "region", "telegram_id", "telegram_username", "gender", "goal",
            "preferred_slot", "current_wake_time", "target_wake_time", "status", "approved_at",
        )}),
        ("Taklif", {"fields": ("referral_code", "referred_by", "referral_immunity_granted")}),
        ("Admin panelga kirish", {"classes": ("collapse",), "fields": (
            "username", "password", "is_active", "is_staff", "is_superuser", "groups", "user_permissions",
        )}),
    )
    readonly_fields = ("approved_at",)
    raw_id_fields = ("referred_by",)

    @admin.display(description="Maqsad")
    def short_goal(self, obj):
        return (obj.goal[:60] + "…") if len(obj.goal) > 60 else obj.goal

    @admin.display(description="Turadi → maqsad")
    def wake_times(self, obj):
        if not obj.current_wake_time:
            return "—"
        return f"{obj.current_wake_time:%H:%M} → {obj.target_wake_time:%H:%M}" if obj.target_wake_time else f"{obj.current_wake_time:%H:%M}"

    @admin.action(description="Qabul qilish (rotaga joylash)")
    def approve(self, request, queryset):
        n = sum(services.approve_user(u) for u in queryset)
        self.message_user(request, f"{n} ta ariza qabul qilindi.")

    @admin.action(description="Rad etish")
    def reject(self, request, queryset):
        n = sum(services.reject_user(u) for u in queryset)
        self.message_user(request, f"{n} ta ariza rad etildi.")

    @admin.action(description="Immunitet berish (+1)")
    def give_immunity(self, request, queryset):
        for u in queryset:
            services.grant_immunity(u, Immunity.Source.ADMIN)
        self.message_user(request, f"{queryset.count()} kishiga Immunitet berildi.")
