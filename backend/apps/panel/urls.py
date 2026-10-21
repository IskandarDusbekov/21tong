from django.urls import path

from . import config_views as cfg
from . import views

urlpatterns = [
    path("session/", views.SessionView.as_view()),
    path("dashboard/", views.DashboardView.as_view()),
    path("applications/", views.ApplicationsView.as_view()),
    path("applications/<int:pk>/<str:decision>/", views.ApplicationDecisionView.as_view()),
    path("members/", views.MembersView.as_view()),
    path("members/<int:pk>/", views.MemberDetailView.as_view()),
    path("members/<int:pk>/action/", views.MemberActionView.as_view()),
    path("squads/", views.SquadsView.as_view()),
    path("settings/", cfg.SettingsView.as_view()),
    path("messages/", cfg.MessagesView.as_view()),
    path("messages/<str:key>/", cfg.MessageView.as_view()),
    path("phrases/", cfg.PhrasesView.as_view()),
    path("phrases/<int:pk>/", cfg.PhraseView.as_view()),
    path("stages/", cfg.StagesView.as_view()),
    path("stages/icons/", cfg.StageIconsView.as_view()),
    path("stages/<int:pk>/", cfg.StageView.as_view()),
    path("cohorts/", cfg.CohortsView.as_view()),
    path("cohorts/<int:pk>/", cfg.CohortView.as_view()),
    path("cohorts/<int:pk>/action/", cfg.CohortActionView.as_view()),
    path("broadcasts/", cfg.BroadcastsView.as_view()),
    path("videos/", cfg.VideosView.as_view()),
    path("videos/<int:pk>/<str:decision>/", cfg.VideoDecisionView.as_view()),
]
