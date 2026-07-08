from django.contrib import admin
from django.core.exceptions import PermissionDenied

from budget.models import Budget
from config.admin_mixins import AuditStampAdminMixin, BudgetAdmin, DeleteDockAdminMixin
from config.permissions import filter_buildings, user_can_access_building


@admin.register(Budget)
class BudgetModelAdmin(DeleteDockAdminMixin, AuditStampAdminMixin, BudgetAdmin):
    list_display = (
        "building",
        "current_supervisor_display",
        "allocated_headcount",
        "actual_headcount_display",
        "variance_display",
        "set_by",
        "updated_at",
    )
    list_filter = ("building",)
    search_fields = ("building__name",)
    autocomplete_fields = ("building",)
    readonly_fields = ("set_by", "updated_at", "created_at")
    fields = ("building", "allocated_headcount", "set_by", "updated_at", "created_at")

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

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "building":
            from buildings.models import Building

            kwargs["queryset"] = filter_buildings(
                Building.objects.order_by("name"),
                request.user,
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not user_can_access_building(request.user, obj.building):
            raise PermissionDenied(
                "You do not have permission to manage budgets for this building."
            )
        obj.set_by = request.user
        # Skip AuditStampAdminMixin so set_by always reflects the last editor.
        super(AuditStampAdminMixin, self).save_model(request, obj, form, change)
