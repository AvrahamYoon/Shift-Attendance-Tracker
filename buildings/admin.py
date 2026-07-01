from django.contrib import admin

from accounts.models import Role
from buildings.models import Building
from config.admin_mixins import BuildingAdmin
from config.permissions import filter_supervisors


@admin.register(Building)
class BuildingModelAdmin(BuildingAdmin):
    list_display = ("name", "address", "supervisor", "active_headcount_display")
    search_fields = ("name", "address", "supervisor__username")
    autocomplete_fields = ("supervisor",)
    fields = ("name", "address", "supervisor")

    @admin.display(description="Active workers")
    def active_headcount_display(self, obj):
        return obj.active_headcount

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "supervisor":
            from accounts.models import User

            kwargs["queryset"] = filter_supervisors(
                User.objects.order_by("username"),
                request.user,
            ).filter(role=Role.SUPERVISOR)
            if request.user.role == Role.DIRECTOR:
                kwargs["queryset"] = User.objects.filter(role=Role.SUPERVISOR).order_by(
                    "username"
                )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.supervisor_id and obj.supervisor.role != Role.SUPERVISOR:
            obj.supervisor = None
            obj.save(update_fields=["supervisor"])
