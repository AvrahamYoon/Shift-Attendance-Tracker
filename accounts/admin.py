from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from unfold.admin import ModelAdmin

from accounts.models import Role, User
from config.permissions import filter_supervisors

# Fields that only a director may change on any user account.
PRIVILEGED_USER_FIELDS = (
    "role",
    "building",
    "manager",
    "is_staff",
    "is_active",
    "is_superuser",
    "username",
)

DIRECTOR_FIELDSETS = (
    (None, {"fields": ("username", "password")}),
    ("Personal info", {"fields": ("first_name", "last_name", "email")}),
    ("Role & assignment", {"fields": ("role", "building", "manager")}),
    ("Admin access", {"fields": ("is_staff", "is_active")}),
    ("Important dates", {"fields": ("last_login", "date_joined")}),
)

SELF_EDIT_FIELDSETS = (
    (None, {"fields": ("username", "password")}),
    ("Personal info", {"fields": ("first_name", "last_name", "email")}),
)

READ_ONLY_USER_FIELDSETS = (
    (None, {"fields": ("username",)}),
    ("Personal info", {"fields": ("first_name", "last_name", "email")}),
    ("Role & assignment", {"fields": ("role", "building", "manager")}),
    ("Admin access", {"fields": ("is_staff", "is_active")}),
)


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    list_display = ("username", "email", "role", "building", "manager", "is_staff")
    list_filter = ("role", "is_staff", "building")
    search_fields = ("username", "first_name", "last_name", "email")
    filter_horizontal = ()

    add_fieldsets = (
        (None, {"fields": ("username", "password1", "password2")}),
        ("Personal info", {"fields": ("first_name", "last_name", "email")}),
        ("Role & assignment", {"fields": ("role", "building", "manager")}),
        ("Admin access", {"fields": ("is_staff", "is_active")}),
    )

    def get_fieldsets(self, request, obj=None):
        if request.user.role == Role.DIRECTOR:
            return DIRECTOR_FIELDSETS
        if obj is None:
            return SELF_EDIT_FIELDSETS
        if obj.pk == request.user.pk:
            return SELF_EDIT_FIELDSETS
        return READ_ONLY_USER_FIELDSETS

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if request.user.role == Role.DIRECTOR:
            return readonly
        if obj is None:
            return readonly + ["username"]
        if obj.pk == request.user.pk:
            return readonly + ["username"]
        return readonly + [
            field.name
            for field in User._meta.fields
            if field.name not in ("id",)
        ]

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

    def save_model(self, request, obj, form, change):
        if request.user.role != Role.DIRECTOR and change:
            original = User.objects.get(pk=obj.pk)
            for field in PRIVILEGED_USER_FIELDS:
                setattr(obj, field, getattr(original, field))
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        if request.user.role != Role.DIRECTOR and change:
            original = User.objects.get(pk=form.instance.pk)
            form.instance.groups.set(original.groups.all())
            form.instance.user_permissions.set(original.user_permissions.all())
