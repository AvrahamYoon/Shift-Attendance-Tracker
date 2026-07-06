# Generated manually for record_time field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("workers", "0007_absence_unique_day"),
    ]

    operations = [
        migrations.AddField(
            model_name="attendancerecord",
            name="record_time",
            field=models.TimeField(
                blank=True,
                help_text="Optional — e.g. arrival time for a tardy, or when the absence was noted.",
                null=True,
            ),
        ),
    ]
