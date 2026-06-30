from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from accounts.models import Role, User
from config.admin_mixins import RoleFilteredAdminMixin
from config.permissions import filter_supervisors


@admin.register(User)
class UserAdmin(BaseUserAdmin, RoleFilteredAdminMixin):
    list_display = ("username", "email", "role", "building", "manager", "is_staff")
    list_filter = ("role", "is_staff", "building")
    search_fields = ("username", "first_name", "last_name", "email")

    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "Role & assignment",
            {"fields": ("role", "building", "manager")},
        ),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (
            "Role & assignment",
            {"fields": ("role", "building", "manager")},
        ),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.role == Role.SUPERVISOR:
            return qs.filter(pk=request.user.pk)
        if request.user.role == Role.MANAGER:
            return filter_supervisors(qs, request.user) | qs.filter(
                pk=request.user.pk
            )
        return qs

    def has_module_permission(self, request):
        return request.user.is_staff and request.user.role in Role.values

    def has_view_permission(self, request, obj=None):
        if obj is None:
            return request.user.is_staff
        if request.user.role == Role.DIRECTOR:
            return request.user.is_staff
        if request.user.role == Role.MANAGER:
            return obj.pk == request.user.pk or (
                obj.role == Role.SUPERVISOR and obj.manager_id == request.user.pk
            )
        if request.user.role == Role.SUPERVISOR:
            return obj.pk == request.user.pk
        return False

    def has_change_permission(self, request, obj=None):
        if request.user.role == Role.DIRECTOR:
            return request.user.is_staff
        if request.user.role in (Role.MANAGER, Role.SUPERVISOR):
            return obj is not None and obj.pk == request.user.pk
        return False

    def has_add_permission(self, request):
        return request.user.role == Role.DIRECTOR and request.user.is_staff

    def has_delete_permission(self, request, obj=None):
        return request.user.role == Role.DIRECTOR and request.user.is_staff
