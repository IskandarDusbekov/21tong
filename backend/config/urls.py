from django.contrib import admin
from django.urls import include, path

from apps.api.urls import app_patterns, bot_patterns

admin.site.site_header = "21tong boshqaruvi"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/bot/", include(bot_patterns)),
    path("api/app/", include(app_patterns)),
]
