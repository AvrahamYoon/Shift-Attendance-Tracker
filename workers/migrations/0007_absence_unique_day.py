from django.conf import settings
from django.db import migrations, models


def dedupe_absence_days(apps, schema_editor):
    AttendanceRecord = apps.get_model("workers", "AttendanceRecord")
    seen = set()
    for record in AttendanceRecord.objects.filter(category="absence").order_by(
        "created_at", "pk"
    ):
        key = (record.worker_id, record.term_id, record.record_date)
        if key in seen:
            record.delete()
        else:
            seen.add(key)


class Migration(migrations.Migration):

    dependencies = [
        ("workers", "0006_remove_position_fields_byui_terms"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(dedupe_absence_days, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="attendancerecord",
            constraint=models.UniqueConstraint(
                condition=models.Q(("category", "absence")),
                fields=("worker", "term", "record_date"),
                name="unique_absence_day_per_worker_term",
            ),
        ),
    ]
