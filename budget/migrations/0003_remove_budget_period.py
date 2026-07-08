from django.db import migrations, models
import django.db.models.deletion


def dedupe_budgets(apps, schema_editor):
    """Keep the newest budget row per building before OneToOne migration."""
    Budget = apps.get_model("budget", "Budget")
    keep_ids = set()
    seen_buildings = set()
    for budget in Budget.objects.order_by("-updated_at", "-pk"):
        if budget.building_id in seen_buildings:
            continue
        seen_buildings.add(budget.building_id)
        keep_ids.add(budget.pk)
    Budget.objects.exclude(pk__in=keep_ids).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("budget", "0002_building_centric_budget"),
    ]

    operations = [
        migrations.RunPython(dedupe_budgets, migrations.RunPython.noop),
        migrations.RemoveConstraint(
            model_name="budget",
            name="unique_building_period_budget",
        ),
        migrations.RemoveField(
            model_name="budget",
            name="period",
        ),
        migrations.AlterField(
            model_name="budget",
            name="building",
            field=models.OneToOneField(
                help_text="Headcount quota for this building.",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="budget",
                to="buildings.building",
            ),
        ),
        migrations.AlterField(
            model_name="budget",
            name="set_by",
            field=models.ForeignKey(
                help_text="Manager who last set this quota.",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="budgets_set",
                to="accounts.user",
            ),
        ),
        migrations.AlterModelOptions(
            name="budget",
            options={"ordering": ["building"]},
        ),
    ]
