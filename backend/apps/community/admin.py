from django.contrib import admin

from .models import Bounty, BountyCompletion, CoinTransaction, Reflection


@admin.register(Reflection)
class ReflectionAdmin(admin.ModelAdmin):
    list_display = ("membership", "date", "text")
    list_filter = ("date",)


@admin.register(Bounty)
class BountyAdmin(admin.ModelAdmin):
    list_display = ("title", "cohort", "date", "reward")
    list_filter = ("cohort", "date")


@admin.register(BountyCompletion)
class BountyCompletionAdmin(admin.ModelAdmin):
    list_display = ("bounty", "membership", "created_at")


@admin.register(CoinTransaction)
class CoinTransactionAdmin(admin.ModelAdmin):
    list_display = ("user", "amount", "reason", "created_at")
