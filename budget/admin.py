from django.contrib import admin

from budget.models import Budget
from config.admin_mixins import AuditStampAdminMixin, BudgetAdmin


@admin.register(Budget)
class BudgetModelAdmin(AuditStampAdminMixin, BudgetAdmin):
    audit_fields = ("set_by",)
    list_display = (
        "period",
        "building",
        "supervisor",
        "allocated_headcount",
        "actual_headcount_display",
        "variance_display",
        "set_by",
    )
    list_filter = ("period", "building")
    search_fields = ("supervisor__username", "building__name")

    @admin.display(description="Actual")
    def actual_headcount_display(self, obj):
        return obj.actual_headcount

    @admin.display(description="Variance")
    def variance_display(self, obj):
        variance = obj.headcount_variance
        prefix = "+" if variance > 0 else ""
        return f"{prefix}{variance}"
