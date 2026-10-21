from django.urls import path

from . import bot, miniapp

bot_patterns = [
    path("users/register/", bot.RegisterView.as_view()),
    path("users/<int:telegram_id>/", bot.UserView.as_view()),
    path("users/<int:telegram_id>/manifest.png", bot.ManifestView.as_view()),
    path("cohorts/recruiting/", bot.RecruitingCohortsView.as_view()),
    path("join/", bot.JoinView.as_view()),
    path("voice/", bot.VoiceView.as_view()),
    path("video/", bot.VideoView.as_view()),
    path("reviews/<int:review_id>/vote/", bot.VoteView.as_view()),
    path("notifications/", bot.NotificationsView.as_view()),
    path("notifications/ack/", bot.NotificationsAckView.as_view()),
    path("alarms/", bot.AlarmsView.as_view()),
    path("windows/", bot.WindowsView.as_view()),
]

app_patterns = [
    path("me/", miniapp.MeView.as_view()),
    path("wake/", miniapp.WakeView.as_view()),
    path("freeze/", miniapp.FreezeView.as_view()),
    path("feed/", miniapp.FeedView.as_view()),
    path("reflections/<int:pk>/fire/", miniapp.FireView.as_view()),
    path("bounties/", miniapp.BountiesView.as_view()),
    path("bounties/<int:pk>/complete/", miniapp.BountyCompleteView.as_view()),
    path("leaderboard/", miniapp.LeaderboardView.as_view()),
    path("dev/users/", miniapp.DevUsersView.as_view()),
]
