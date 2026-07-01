from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def copy_m2m_to_building_supervisor(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    Building = apps.get_model("buildings", "Building")
    for user in User.objects.filter(role="supervisor"):
        for building in user.buildings.all():
            building.supervisor_id = user.pk
            building.save(update_fields=["supervisor_id"])


class Migration(migrations.Migration):

    dependencies = [
        ("buildings", "0001_initial"),
        ("accounts", "0002_user_buildings_m2m"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="building",
            name="supervisor",
            field=models.ForeignKey(
                blank=True,
                help_text="The one supervisor responsible for this building.",
                limit_choices_to={"role": "supervisor"},
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="supervised_buildings",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(copy_m2m_to_building_supervisor, migrations.RunPython.noop),
    ]
