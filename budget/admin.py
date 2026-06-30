from django.contrib import admin

from budget.models import Budget
from config.admin_mixins import AuditStampAdminMixin, BudgetAdmin


@admin.register(Budget)
class BudgetModelAdmin(AuditStampAdminMixin, BudgetAdmin):
    audit_fields = ("set_by",)
    list_display = (
        "period",
        "building",
        "current_supervisor_display",
        "allocated_headcount",
        "actual_headcount_display",
        "variance_display",
        "set_by",
    )
    list_filter = ("period", "building")
    search_fields = ("building__name",)
    autocomplete_fields = ("building",)

    @admin.display(description="Current supervisor")
    def current_supervisor_display(self, obj):
        supervisor = obj.current_supervisor
        return supervisor.get_full_name() or supervisor.username if supervisor else "—"

    @admin.display(description="Actual")
    def actual_headcount_display(self, obj):
        return obj.actual_headcount

    @admin.display(description="Variance")
    def variance_display(self, obj):
        variance = obj.headcount_variance
        prefix = "+" if variance > 0 else ""
        return f"{prefix}{variance}"
