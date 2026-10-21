from django.contrib import admin
from django.db.models import Count

from .models import Bounty, BountyCompletion, CoinTransaction, Reflection


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
