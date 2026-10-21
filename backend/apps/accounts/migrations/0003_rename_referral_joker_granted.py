from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_user_current_wake_time_user_target_wake_time"),
    ]

    operations = [
        migrations.RenameField("user", "referral_joker_granted", "referral_immunity_granted"),
    ]
