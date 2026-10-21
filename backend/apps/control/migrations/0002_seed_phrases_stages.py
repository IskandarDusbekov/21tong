from django.db import migrations

from apps.control import defaults


def seed(apps, schema_editor):
    Phrase = apps.get_model("control", "Phrase")
    Stage = apps.get_model("control", "Stage")
    CampSettings = apps.get_model("control", "CampSettings")
    if not Phrase.objects.exists():
        Phrase.objects.bulk_create([Phrase(text=t) for t in defaults.PHRASES])
    if not Stage.objects.exists():
        Stage.objects.bulk_create([
            Stage(day=day, name=name, description=desc, icon=icon) for day, name, desc, icon in defaults.STAGES
        ])
    CampSettings.objects.get_or_create(pk=1)


class Migration(migrations.Migration):
    dependencies = [("control", "0001_initial")]

    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
