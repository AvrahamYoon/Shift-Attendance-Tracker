from django.contrib import admin
from django.core.exceptions import PermissionDenied

from accounts.models import Role, User
from buildings.models import Building
from config.admin_mixins import BuildingAdmin, DeleteDockAdminMixin
from config.permissions import (
    filter_supervisors,
    has_director_access,
    user_can_access_building,
)


@admin.register(Building)
class BuildingModelAdmin(DeleteDockAdminMixin, BuildingAdmin):
    list_display = ("name", "address", "supervisor", "active_headcount_display")
    search_fields = ("name", "address", "supervisor__username")
    autocomplete_fields = ("supervisor",)
    fields = ("name", "address", "supervisor")

    @admin.display(description="Active workers")
    def active_headcount_display(self, obj):
        return obj.active_headcount

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "supervisor":
            kwargs["queryset"] = filter_supervisors(
                User.objects.filter(role=Role.SUPERVISOR).order_by("username"),
                request.user,
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def has_delete_permission(self, request, obj=None):
        return has_director_access(request.user)

    def save_model(self, request, obj, form, change):
        if obj.supervisor_id:
            if obj.supervisor.role != Role.SUPERVISOR:
                raise PermissionDenied(
                    "Building supervisor must have the Supervisor role."
                )
            if request.user.role == Role.MANAGER:
                if obj.supervisor.manager_id != request.user.pk:
                    raise PermissionDenied(
                        "Managers may only assign their own supervisors to a building."
                    )
        if (
            change
            and request.user.role == Role.MANAGER
            and not has_director_access(request.user)
        ):
            original = Building.objects.filter(pk=obj.pk).first()
            if original and not user_can_access_building(request.user, original):
                raise PermissionDenied(
                    "You do not have permission to edit this building."
                )
        super().save_model(request, obj, form, change)
