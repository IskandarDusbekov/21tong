from django.contrib import admin
from django.db.models import Count

from .models import (
    Bounty, BountyCompletion, CoinTransaction, PhotoChallenge, PhotoEntry, Reflection, SquadMessage,
)


@admin.register(PhotoChallenge)
class PhotoChallengeAdmin(admin.ModelAdmin):
    list_display = ("date", "title", "cohort", "theme", "max_entries", "entries_count")
    list_filter = ("cohort", "date")
    date_hierarchy = "date"

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(n=Count("entries"))

    @admin.display(description="Rasmlar", ordering="n")
    def entries_count(self, obj):
        return obj.n


@admin.register(PhotoEntry)
class PhotoEntryAdmin(admin.ModelAdmin):
    list_display = ("challenge", "membership", "votes", "created_at")
    list_filter = ("challenge__cohort",)
    raw_id_fields = ("challenge", "membership")

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(n=Count("votes"))

    @admin.display(description="Ovozlar", ordering="n")
    def votes(self, obj):
        return obj.n


@admin.register(SquadMessage)
class SquadMessageAdmin(admin.ModelAdmin):
    list_display = ("squad", "author", "text", "created_at")
    list_filter = ("squad__tribe__cohort", "created_at")
    search_fields = ("text", "author__user__first_name")
    raw_id_fields = ("squad", "author")


@admin.register(Reflection)
class ReflectionAdmin(admin.ModelAdmin):
    list_display = ("membership", "date", "text", "fires")
    list_filter = ("date", "membership__cohort", "membership__squad")
    search_fields = ("text", "membership__user__first_name")

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(n_fires=Count("fires"))

    @admin.display(description="Olov", ordering="n_fires")
    def fires(self, obj):
        return obj.n_fires


@admin.register(Bounty)
class BountyAdmin(admin.ModelAdmin):
    list_display = ("title", "cohort", "date", "reward", "done")
    list_filter = ("cohort", "date")
    date_hierarchy = "date"

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(n_done=Count("completions"))

    @admin.display(description="Bajardi", ordering="n_done")
    def done(self, obj):
        return obj.n_done


@admin.register(BountyCompletion)
class BountyCompletionAdmin(admin.ModelAdmin):
    list_display = ("bounty", "membership", "created_at")
    list_filter = ("bounty__cohort",)


@admin.register(CoinTransaction)
class CoinTransactionAdmin(admin.ModelAdmin):
    list_display = ("user", "amount", "reason", "created_at")
    list_filter = ("reason",)
    raw_id_fields = ("user", "bounty_completion")
