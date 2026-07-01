from django.conf import settings
from django.db import migrations, models


def copy_building_to_buildings(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    for user in User.objects.exclude(building_id=None):
        user.buildings.add(user.building_id)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
        ("buildings", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="buildings",
            field=models.ManyToManyField(
                blank=True,
                help_text="Buildings this supervisor is allowed to manage.",
                related_name="supervisor_users",
                to="buildings.building",
            ),
        ),
        migrations.RunPython(copy_building_to_buildings, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="user",
            name="building",
        ),
    ]
