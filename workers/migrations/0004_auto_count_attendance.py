from datetime import date

from django.db import migrations, models
import django.db.models.deletion


def create_term_and_backfill(apps, schema_editor):
    Term = apps.get_model("workers", "Term")
    AttendanceRecord = apps.get_model("workers", "AttendanceRecord")
    term, _ = Term.objects.get_or_create(
        name="2026 Spring",
        defaults={
            "start_date": date(2026, 1, 10),
            "end_date": date(2026, 5, 20),
        },
    )
    for record in AttendanceRecord.objects.filter(term__isnull=True):
        matched = Term.objects.filter(
            start_date__lte=record.record_date,
            end_date__gte=record.record_date,
        ).first()
        record.term = matched or term
        record.save(update_fields=["term"])


class Migration(migrations.Migration):

    dependencies = [
        ("workers", "0003_clarify_position_slot_help"),
    ]

    operations = [
        migrations.CreateModel(
            name="Term",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text='e.g. "2026 Spring"',
                        max_length=100,
                    ),
                ),
                ("start_date", models.DateField()),
                ("end_date", models.DateField()),
            ],
            options={
                "ordering": ["-start_date"],
            },
        ),
        migrations.AddField(
            model_name="attendancerecord",
            name="term",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="attendance_records",
                to="workers.term",
            ),
        ),
        migrations.RunPython(create_term_and_backfill, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="attendancerecord",
            name="term",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="attendance_records",
                to="workers.term",
            ),
        ),
        migrations.RemoveField(
            model_name="attendancerecord",
            name="subtype",
        ),
    ]
