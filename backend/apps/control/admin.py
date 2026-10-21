from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import format_html, format_html_join

from .models import SETTINGS_GROUPS, BotMessage, Broadcast, CampSettings, Phrase, Stage
from .services import send_broadcast


@admin.register(CampSettings)
class CampSettingsAdmin(admin.ModelAdmin):
    fieldsets = [(title, {"fields": fields}) for title, _, fields in SETTINGS_GROUPS]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        # Ro'yxat o'rniga to'g'ridan-to'g'ri yagona yozuvni ochamiz
        CampSettings.load()
        return redirect(reverse("admin:control_campsettings_change", args=[1]))

    def response_change(self, request, obj):
        self.message_user(request, "Sozlamalar saqlandi. Bot va Mini App 30 soniya ichida yangi qiymatlarga o'tadi.")
        return redirect(request.path)


@admin.register(Phrase)
class PhraseAdmin(admin.ModelAdmin):
    list_display = ("text", "is_active")
    list_editable = ("is_active",)
    search_fields = ("text",)
    list_filter = ("is_active",)


@admin.register(Stage)
class StageAdmin(admin.ModelAdmin):
    list_display = ("day", "name", "description", "icon")
    list_display_links = ("name",)
    list_editable = ("day", "icon")


@admin.register(BotMessage)
class BotMessageAdmin(admin.ModelAdmin):
    list_display = ("title", "group", "preview", "is_changed", "updated_at")
    list_filter = ("group",)
    search_fields = ("title", "text", "key")
    readonly_fields = ("key", "group", "title", "variables_help", "default_preview")
    fields = ("title", "group", "key", "text", "variables_help", "default_preview")
    actions = ["reset_to_default"]

    def has_add_permission(self, request):
        return False  # xabarlar ro'yxati kodda — faqat matni tahrirlanadi

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Matn")
    def preview(self, obj):
        return obj.text[:90] + ("…" if len(obj.text) > 90 else "")

    @admin.display(description="O'zgartirilgan", boolean=True)
    def is_changed(self, obj):
        return obj.text != obj.default_text

    @admin.display(description="Ishlatish mumkin bo'lgan o'zgaruvchilar")
    def variables_help(self, obj):
        return format_html_join(" ", "<code>{{{}}}</code>", ((v,) for v in obj.variables))

    @admin.display(description="Standart matn")
    def default_preview(self, obj):
        return format_html("<pre style='white-space:pre-wrap;margin:0'>{}</pre>", obj.default_text)

    @admin.action(description="Standart matnga qaytarish")
    def reset_to_default(self, request, queryset):
        for m in queryset:
            m.text = m.default_text
            m.save(update_fields=["text", "updated_at"])
        self.message_user(request, f"{queryset.count()} ta xabar standart matnga qaytarildi.")


@admin.register(Broadcast)
class BroadcastAdmin(admin.ModelAdmin):
    list_display = ("short_text", "audience", "gender", "sent_count", "created_at")
    fields = ("audience", "cohort", "squad", "gender", "text", "sent_count")
    readonly_fields = ("sent_count",)

    @admin.display(description="Xabar")
    def short_text(self, obj):
        return str(obj)

    def has_change_permission(self, request, obj=None):
        return obj is None  # yuborilgan xabarni o'zgartirib bo'lmaydi

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change:
            n = send_broadcast(obj)
            messages.success(request, f"Xabar {n} kishiga navbatga qo'yildi — bot bir necha soniyada yuboradi.")

    def render_change_form(self, request, context, add=False, change=False, form_url="", obj=None):
        if add:
            context["subtitle"] = "Saqlash tugmasi xabarni darhol yuboradi."
        return super().render_change_form(request, context, add, change, form_url, obj)

