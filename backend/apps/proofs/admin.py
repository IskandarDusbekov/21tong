from django.contrib import admin
from django.utils import timezone

from apps.camp.models import Notification
from apps.camp.services import notify

from .models import Review, VideoProof


class ReviewInline(admin.TabularInline):
    model = Review
    extra = 0
    readonly_fields = ("reviewer", "approved", "assigned_at", "voted_at")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(VideoProof)
class VideoProofAdmin(admin.ModelAdmin):
    list_display = ("day", "status", "votes", "uploaded_at", "decided_at")
    list_filter = ("status", "day__membership__cohort", "day__membership__squad")
    search_fields = ("day__membership__user__first_name", "day__membership__user__telegram_username")
    readonly_fields = ("day", "telegram_file_id", "duration", "uploaded_at", "decided_at", "admin_reviewed_at")
    inlines = [ReviewInline]
    actions = ["mark_reviewed", "approve", "reject"]

    @admin.action(description="Admin tekshirdi deb belgilash (chatda hammaga ko'rinadi)")
    def mark_reviewed(self, request, queryset):
        from apps.camp.services import admin_review_report
        n = sum(admin_review_report(p.day) for p in queryset.select_related("day"))
        self.message_user(request, f"{n} ta video «Admin tekshirdi» deb belgilandi.")

    @admin.display(description="Ovozlar (✔/✘/kutilmoqda)")
    def votes(self, obj):
        v = list(obj.reviews.values_list("approved", flat=True))
        return f"{v.count(True)}/{v.count(False)}/{v.count(None)}"

    def _decide(self, request, queryset, status, kind):
        for proof in queryset.select_related("day__membership__user"):
            proof.status = status
            proof.decided_at = timezone.now()
            proof.save(update_fields=["status", "decided_at"])
            notify(proof.day.membership.user, kind, day_number=proof.day.day_number)
        self.message_user(request, f"{queryset.count()} ta video: {VideoProof.Status(status).label}.")

    @admin.action(description="Qo'lda tasdiqlash")
    def approve(self, request, queryset):
        self._decide(request, queryset, VideoProof.Status.APPROVED, Notification.Kind.VIDEO_APPROVED)

    @admin.action(description="Qo'lda rad etish")
    def reject(self, request, queryset):
        self._decide(request, queryset, VideoProof.Status.REJECTED, Notification.Kind.VIDEO_REJECTED)
