from django.db import migrations


def renumber(apps, schema_editor):
    """Mavjud rotalarni oqim bo'yicha qayta raqamlash — boshqa qabiladagi rota bilan nom takrorlanmasin."""
    Squad = apps.get_model("camp", "Squad")
    Cohort = apps.get_model("camp", "Cohort")
    for cohort in Cohort.objects.all():
        squads = list(
            Squad.objects.filter(tribe__cohort=cohort)
            .order_by("tribe__start_wake_time", "tribe__gender", "number", "id")
        )
        # Avval vaqtinchalik raqam — (tribe, number) unikalligi o'rtada buzilmasin
        for s in squads:
            s.number += 10000
            s.save(update_fields=["number"])
        for i, s in enumerate(squads, 1):
            s.number = i
            s.save(update_fields=["number"])


class Migration(migrations.Migration):

    dependencies = [
        ('camp', '0007_dayrecord_water_at_dayrecord_water_photo'),
    ]

    operations = [
        migrations.RunPython(renumber, migrations.RunPython.noop),
    ]
