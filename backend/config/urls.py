from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

from apps.api.urls import app_patterns, bot_patterns

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/bot/", include(bot_patterns)),
    path("api/app/", include(app_patterns)),
    path("api/panel/", include("apps.panel.urls")),
]

if settings.DEBUG:
    # Lokal ishlab chiqish: `npm run build` qilingan panel http://localhost:8000/panel/ da
    urlpatterns += [
        re_path(r"^panel/assets/(?P<path>.*)$", serve, {"document_root": settings.PANEL_DIST / "assets"}),
        re_path(r"^panel/.*$", serve, {"path": "index.html", "document_root": settings.PANEL_DIST}),
    ]

if settings.DEV_LOGIN:
    # Lokal ishlab chiqish: `npm run build` qilingan Mini App runserver orqali http://localhost:8000/ da
    urlpatterns += [
        re_path(r"^assets/(?P<path>.*)$", serve, {"document_root": settings.MINIAPP_DIST / "assets"}),
        path("", serve, {"path": "index.html", "document_root": settings.MINIAPP_DIST}),
    ]
