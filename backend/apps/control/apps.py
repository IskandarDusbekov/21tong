from django.apps import AppConfig
from django.db.models.signals import post_migrate


def sync_bot_messages(sender, **kwargs):
    from .models import BotMessage, CampSettings

    CampSettings.load()
    BotMessage.sync_defaults()


class ControlConfig(AppConfig):
    name = "apps.control"
    verbose_name = "Boshqaruv"

    def ready(self):
        post_migrate.connect(sync_bot_messages, sender=self)
