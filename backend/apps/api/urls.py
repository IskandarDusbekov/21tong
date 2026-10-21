from django.urls import path

from . import bot, miniapp

bot_patterns = [
    path("config/", bot.ConfigView.as_view()),
    path("users/register/", bot.RegisterView.as_view()),
    path("users/pending/", bot.PendingApplicationsView.as_view()),
    path("users/<int:telegram_id>/", bot.UserView.as_view()),
    path("users/<int:telegram_id>/approve/", bot.ApproveView.as_view()),
    path("users/<int:telegram_id>/reject/", bot.RejectView.as_view()),
    path("users/<int:telegram_id>/manifest.png", bot.ManifestView.as_view()),
    path("cohorts/recruiting/", bot.RecruitingCohortsView.as_view()),
    path("slots/", bot.SlotsView.as_view()),
    path("awards/<int:pk>.png", bot.AwardImageView.as_view()),
    path("countdown/", bot.CountdownView.as_view()),
    path("run-daily/", bot.RunDailyView.as_view()),
    path("join/", bot.JoinView.as_view()),
    path("wake/", bot.WakeView.as_view()),
    path("voice/", bot.VoiceView.as_view()),
    path("video/", bot.VideoView.as_view()),
    path("reviews/<int:review_id>/vote/", bot.VoteView.as_view()),
    path("notifications/", bot.NotificationsView.as_view()),
    path("notifications/ack/", bot.NotificationsAckView.as_view()),
    path("alarms/", bot.AlarmsView.as_view()),
]

app_patterns = [
    path("me/", miniapp.MeView.as_view()),
    path("wake/", miniapp.WakeView.as_view()),
    path("freeze/", miniapp.FreezeView.as_view()),
    path("squad/", miniapp.SquadView.as_view()),
    path("chat/", miniapp.ChatView.as_view()),
    path("media/<str:kind>/<int:pk>/", miniapp.ProofMediaView.as_view()),
    path("feed/", miniapp.FeedView.as_view()),
    path("reflections/<int:pk>/fire/", miniapp.FireView.as_view()),
    path("bounties/", miniapp.BountiesView.as_view()),
    path("bounties/<int:pk>/complete/", miniapp.BountyCompleteView.as_view()),
    path("photos/", miniapp.PhotosView.as_view()),
    path("photos/<int:pk>/vote/", miniapp.PhotoVoteView.as_view()),
    path("photos/<int:pk>.jpg", miniapp.PhotoImageView.as_view()),
    path("leaderboard/", miniapp.LeaderboardView.as_view()),
    path("awards/<int:pk>.png", miniapp.AwardImageView.as_view()),
    path("dev/users/", miniapp.DevUsersView.as_view()),
]
