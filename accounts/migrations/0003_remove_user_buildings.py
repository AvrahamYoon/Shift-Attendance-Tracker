from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_user_buildings_m2m"),
        ("buildings", "0002_building_supervisor"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="user",
            name="buildings",
        ),
    ]
