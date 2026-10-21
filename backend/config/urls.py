from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

from apps.api.urls import app_patterns, bot_patterns

admin.site.site_header = "21tong boshqaruvi"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/bot/", include(bot_patterns)),
    path("api/app/", include(app_patterns)),
]

if settings.DEV_LOGIN:
    # Lokal ishlab chiqish: `npm run build` qilingan Mini App runserver orqali http://localhost:8000/ da
    urlpatterns += [
        re_path(r"^assets/(?P<path>.*)$", serve, {"document_root": settings.MINIAPP_DIST / "assets"}),
        path("", serve, {"path": "index.html", "document_root": settings.MINIAPP_DIST}),
    ]
