from django.db import migrations

from apps.control import defaults


def apply(apps, schema_editor):
    """Mavjud bosqichlarga standart mukofot va unvonlarni beradi; do'st taklifi uchun Immunitetni o'chiradi."""
    Stage = apps.get_model("control", "Stage")
    for day, _name, _desc, _icon, award_type, rank, stars in defaults.STAGES:
        Stage.objects.filter(day=day, rank="").update(award_type=award_type, rank=rank, stars=stars)
    apps.get_model("control", "CampSettings").objects.update(referral_immunity=False)


class Migration(migrations.Migration):
    dependencies = [("control", "0003_botmessage_customized_stage_award_type_stage_rank_and_more")]

    operations = [migrations.RunPython(apply, migrations.RunPython.noop)]
