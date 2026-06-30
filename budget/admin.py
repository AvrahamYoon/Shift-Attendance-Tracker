from django.contrib import admin

from budget.models import Budget
from config.admin_mixins import BudgetAdmin


@admin.register(Budget)
class BudgetModelAdmin(BudgetAdmin):
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

    def save_model(self, request, obj, form, change):
        if not change:
            obj.set_by = request.user
        super().save_model(request, obj, form, change)

    def has_add_permission(self, request):
        return request.user.role in ("director", "manager") and request.user.is_staff

    def has_change_permission(self, request, obj=None):
        return request.user.role in ("director", "manager") and request.user.is_staff

    def has_delete_permission(self, request, obj=None):
        return request.user.role == "director" and request.user.is_staff
