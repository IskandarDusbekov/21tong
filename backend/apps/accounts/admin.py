from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.camp import services

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("__str__", "telegram_id", "gender", "status", "short_goal", "date_joined")
    list_filter = ("status", "gender", "is_staff")
    search_fields = ("username", "telegram_username", "telegram_id", "goal")
    actions = ["approve", "reject"]
    fieldsets = BaseUserAdmin.fieldsets + (
        ("21tong", {"fields": (
            "telegram_id", "telegram_username", "gender", "goal", "current_wake_time", "target_wake_time", "status",
            "referral_code", "referred_by", "referral_joker_granted", "approved_at",
        )}),
    )
    readonly_fields = ("approved_at",)

    @admin.display(description="Maqsad")
    def short_goal(self, obj):
        return (obj.goal[:60] + "…") if len(obj.goal) > 60 else obj.goal

    @admin.action(description="Tasdiqlash (yopiq guruhga yo'llanma)")
    def approve(self, request, queryset):
        n = sum(services.approve_user(u) for u in queryset)
        self.message_user(request, f"{n} ta foydalanuvchi tasdiqlandi.")

    @admin.action(description="Rad etish")
    def reject(self, request, queryset):
        n = sum(services.reject_user(u) for u in queryset)
        self.message_user(request, f"{n} ta foydalanuvchi rad etildi.")
