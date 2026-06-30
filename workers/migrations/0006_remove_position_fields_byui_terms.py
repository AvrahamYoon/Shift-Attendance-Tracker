from django.db import migrations


def sync_terms(apps, schema_editor):
    Term = apps.get_model("workers", "Term")
    from workers.byui_terms import sync_byui_terms

    sync_byui_terms(Term)


class Migration(migrations.Migration):

    dependencies = [
        ("workers", "0005_optional_record_date"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="worker",
            name="is_lead",
        ),
        migrations.RemoveField(
            model_name="worker",
            name="position_number",
        ),
        migrations.AlterModelOptions(
            name="worker",
            options={"ordering": ["building", "name"]},
        ),
        migrations.RunPython(sync_terms, migrations.RunPython.noop),
    ]
