from django.db import migrations


def rename_kinds(apps, schema_editor):
    Notification = apps.get_model("camp", "Notification")
    Notification.objects.filter(kind="joker_used").update(kind="immunity_used")
    Notification.objects.filter(kind="joker_granted").update(kind="immunity_granted")


class Migration(migrations.Migration):
    """"Joker" o'rniga jiddiyroq nom — "Immunitet"."""

    dependencies = [
        ("camp", "0002_remove_tribe_invite_link_and_more"),
    ]

    operations = [
        migrations.RenameModel("Joker", "Immunity"),
        migrations.RenameField("strike", "cancelled_by_joker", "cancelled_by_immunity"),
        migrations.RunPython(rename_kinds, migrations.RunPython.noop),
    ]
