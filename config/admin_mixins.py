from unfold.admin import ModelAdmin, TabularInline

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


class AuditStampAdminMixin:
    """Auto-stamp who created a record and prevent changing it later."""

    audit_fields = ()

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        for field in self.audit_fields:
            if field not in readonly:
                readonly.append(field)
        return readonly

    def save_model(self, request, obj, form, change):
        self._apply_audit_fields(request, obj, change)
        super().save_model(request, obj, form, change)

    def _apply_audit_fields(self, request, obj, change):
        if not self.audit_fields:
            return
        if change:
            original = obj.__class__.objects.filter(pk=obj.pk).first()
            if original:
                for field in self.audit_fields:
                    setattr(obj, field, getattr(original, field))
        else:
            for field in self.audit_fields:
                setattr(obj, field, request.user)


class InlineAuditStampMixin:
    """Stamp audit fields on tabular inlines; keep them off the editable form."""

    audit_field = None

    def get_fields(self, request, obj=None):
        fields = list(super().get_fields(request, obj))
        if self.audit_field and self.audit_field in fields:
            fields.remove(self.audit_field)
        return fields

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if obj is not None and self.audit_field and self.audit_field not in readonly:
            readonly.append(self.audit_field)
        return readonly


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


class WorkerRelatedAdmin(RoleFilteredAdminMixin, ModelAdmin):
    permission_filter = filter_by_worker_relation
    list_filter_submit = True


class WorkerAdmin(RoleFilteredAdminMixin, ModelAdmin):
    permission_filter = filter_workers
    list_filter_submit = True


class BuildingAdmin(RoleFilteredAdminMixin, ModelAdmin):
    permission_filter = filter_buildings
    role_permissions = {
        Role.DIRECTOR: FULL_ACCESS,
        Role.MANAGER: VIEW_ONLY,
        Role.SUPERVISOR: VIEW_ONLY,
    }


class NoteAdmin(RoleFilteredAdminMixin, ModelAdmin):
    permission_filter = filter_notes
    list_filter_submit = True


class BudgetAdmin(RoleFilteredAdminMixin, ModelAdmin):
    permission_filter = filter_budgets
    role_permissions = {
        Role.DIRECTOR: FULL_ACCESS,
        Role.MANAGER: MANAGER_BUDGET_ACCESS,
        Role.SUPERVISOR: VIEW_ONLY,
    }
