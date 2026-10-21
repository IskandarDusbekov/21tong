from django.contrib import admin

from .models import Review, VideoProof


class ReviewInline(admin.TabularInline):
    model = Review
    extra = 0
    readonly_fields = ("reviewer", "approved", "assigned_at", "voted_at")


@admin.register(VideoProof)
class VideoProofAdmin(admin.ModelAdmin):
    list_display = ("day", "status", "uploaded_at", "decided_at")
    list_filter = ("status",)
    inlines = [ReviewInline]
