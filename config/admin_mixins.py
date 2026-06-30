from django.contrib import admin

from accounts.models import Role
from config.permissions import (
    filter_budgets,
    filter_buildings,
    filter_by_worker_relation,
    filter_notes,
    filter_workers,
)

FULL_ACCESS = ("view", "add", "change", "delete")
VIEW_ONLY = ("view",)
SUPERVISOR_WORKER_ACCESS = ("view", "add", "change")
MANAGER_BUDGET_ACCESS = ("view", "add", "change")


def staff_with_role(request):
    return (
        request.user.is_active
        and request.user.is_staff
        and getattr(request.user, "role", None)
        in (Role.DIRECTOR, Role.MANAGER, Role.SUPERVISOR)
    )


class RoleFilteredAdminMixin:
    """Role-based queryset filtering and admin permissions without Django perms."""

    permission_filter = None
    role_permissions = {
        Role.DIRECTOR: FULL_ACCESS,
        Role.MANAGER: VIEW_ONLY,
        Role.SUPERVISOR: SUPERVISOR_WORKER_ACCESS,
    }

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Access on the class so the filter is not bound to this ModelAdmin instance.
        permission_filter = type(self).permission_filter
        if permission_filter:
            return permission_filter(qs, request.user)
        return qs

    def _role_allows(self, request, action):
        allowed = self.role_permissions.get(request.user.role, ())
        return action in allowed

    def has_module_permission(self, request):
        return staff_with_role(request) and self._role_allows(request, "view")

    def has_view_permission(self, request, obj=None):
        return staff_with_role(request) and self._role_allows(request, "view")

    def has_add_permission(self, request):
        return staff_with_role(request) and self._role_allows(request, "add")

    def has_change_permission(self, request, obj=None):
        return staff_with_role(request) and self._role_allows(request, "change")

    def has_delete_permission(self, request, obj=None):
        return staff_with_role(request) and self._role_allows(request, "delete")


class WorkerRelatedAdmin(RoleFilteredAdminMixin, admin.ModelAdmin):
    permission_filter = filter_by_worker_relation


class WorkerAdmin(RoleFilteredAdminMixin, admin.ModelAdmin):
    permission_filter = filter_workers


class BuildingAdmin(RoleFilteredAdminMixin, admin.ModelAdmin):
    permission_filter = filter_buildings
    role_permissions = {
        Role.DIRECTOR: FULL_ACCESS,
        Role.MANAGER: VIEW_ONLY,
        Role.SUPERVISOR: VIEW_ONLY,
    }


class NoteAdmin(RoleFilteredAdminMixin, admin.ModelAdmin):
    permission_filter = filter_notes


class BudgetAdmin(RoleFilteredAdminMixin, admin.ModelAdmin):
    permission_filter = filter_budgets
    role_permissions = {
        Role.DIRECTOR: FULL_ACCESS,
        Role.MANAGER: MANAGER_BUDGET_ACCESS,
        Role.SUPERVISOR: VIEW_ONLY,
    }
