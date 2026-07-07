from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.core.exceptions import PermissionDenied
from unfold.admin import ModelAdmin

from accounts.forms import (
    DirectorUserCreationForm,
    ManagerSupervisorCreationForm,
    ScopedUserChangeForm,
)
from accounts.models import Role, User
from config.permissions import filter_supervisors, has_director_access

# Fields that only a director may change on any user account.
PRIVILEGED_USER_FIELDS = (
    "role",
    "manager",
    "is_staff",
    "is_active",
    "is_superuser",
    "username",
)

DIRECTOR_FIELDSETS = (
    (None, {"fields": ("username", "password")}),
    ("Personal info", {"fields": ("first_name", "last_name", "email")}),
    (
        "Role & assignment",
        {
            "fields": ("role", "manager", "supervised_buildings_display"),
            "description": (
                "Directors create managers and supervisors here. Assign buildings "
                "on the Buildings screen — each building has exactly one supervisor."
            ),
        },
    ),
    ("Admin access", {"fields": ("is_staff", "is_active")}),
    ("Important dates", {"fields": ("last_login", "date_joined")}),
)

MANAGER_SUPERVISOR_FIELDSETS = (
    (None, {"fields": ("username", "password")}),
    ("Personal info", {"fields": ("first_name", "last_name", "email")}),
    (
        "Role & assignment",
        {
            "fields": ("role", "manager", "supervised_buildings_display"),
            "description": (
                "This account is a supervisor on your team. Assign their building(s) "
                "under Buildings."
            ),
        },
    ),
    ("Admin access", {"fields": ("is_staff", "is_active")}),
)

SELF_EDIT_FIELDSETS = (
    (None, {"fields": ("username", "password")}),
    ("Personal info", {"fields": ("first_name", "last_name", "email")}),
)

READ_ONLY_USER_FIELDSETS = (
    (None, {"fields": ("username",)}),
    ("Personal info", {"fields": ("first_name", "last_name", "email")}),
    (
        "Role & assignment",
        {"fields": ("role", "supervised_buildings_display", "manager")},
    ),
    ("Admin access", {"fields": ("is_staff", "is_active")}),
)


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = ScopedUserChangeForm
    list_display = (
        "username",
        "email",
        "role",
        "supervised_buildings_display",
        "manager",
        "is_staff",
    )
    list_filter = ("role", "is_staff")
    search_fields = ("username", "first_name", "last_name", "email")
    filter_horizontal = ()

    add_fieldsets = (
        (None, {"fields": ("username", "password1", "password2")}),
        ("Personal info", {"fields": ("first_name", "last_name", "email")}),
        (
            "Role & assignment",
            {
                "fields": ("role", "manager"),
                "description": (
                    "Create a Manager (no manager field) or a Supervisor "
                    "(must pick their manager)."
                ),
            },
        ),
        ("Admin access", {"fields": ("is_staff", "is_active")}),
    )

    def get_form(self, request, obj=None, **kwargs):
        if obj is None:
            if request.user.role == Role.MANAGER:
                manager_user = request.user

                class ManagerForm(ManagerSupervisorCreationForm):
                    def __init__(self, *args, **kw):
                        super().__init__(
                            *args, manager_user=manager_user, **kw
                        )

                kwargs["form"] = ManagerForm
            elif has_director_access(request.user):
                kwargs["form"] = DirectorUserCreationForm
        return super().get_form(request, obj, **kwargs)

    def get_fieldsets(self, request, obj=None):
        if has_director_access(request.user):
            if obj is None:
                return self.add_fieldsets
            return DIRECTOR_FIELDSETS
        if request.user.role == Role.MANAGER:
            if obj is None:
                return (
                    (None, {"fields": ("username", "password1", "password2")}),
                    (
                        "Personal info",
                        {"fields": ("first_name", "last_name", "email")},
                    ),
                )
            if obj.pk == request.user.pk:
                return SELF_EDIT_FIELDSETS
            if obj.role == Role.SUPERVISOR and obj.manager_id == request.user.pk:
                return MANAGER_SUPERVISOR_FIELDSETS
        if obj is None:
            return SELF_EDIT_FIELDSETS
        if obj.pk == request.user.pk:
            return SELF_EDIT_FIELDSETS
        return READ_ONLY_USER_FIELDSETS

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if has_director_access(request.user) and obj is not None:
            readonly.append("supervised_buildings_display")
            return readonly
        if (
            request.user.role == Role.MANAGER
            and obj is not None
            and obj.pk != request.user.pk
            and obj.role == Role.SUPERVISOR
            and obj.manager_id == request.user.pk
        ):
            return readonly + [
                "role",
                "manager",
                "is_staff",
                "is_active",
                "supervised_buildings_display",
            ]
        if obj is None:
            return readonly
        if obj.pk == request.user.pk:
            return readonly + ["username"]
        return readonly + [
            field.name for field in User._meta.fields if field.name != "id"
        ] + ["supervised_buildings_display"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if has_director_access(request.user):
            return qs
        if request.user.role == Role.SUPERVISOR:
            return qs.filter(pk=request.user.pk)
        if request.user.role == Role.MANAGER:
            return filter_supervisors(qs, request.user) | qs.filter(
                pk=request.user.pk
            )
        return qs.none()

    @admin.display(description="Buildings")
    def supervised_buildings_display(self, obj):
        return (
            ", ".join(
                obj.supervised_buildings.order_by("name").values_list("name", flat=True)
            )
            or "—"
        )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "manager" and has_director_access(request.user):
            kwargs["queryset"] = User.objects.filter(role=Role.MANAGER).order_by(
                "username"
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def has_module_permission(self, request):
        return request.user.is_staff and request.user.role in Role.values

    def has_view_permission(self, request, obj=None):
        if not request.user.is_staff:
            return False
        if obj is None:
            return request.user.role in Role.values
        if has_director_access(request.user):
            return True
        if request.user.role == Role.MANAGER:
            return obj.pk == request.user.pk or (
                obj.role == Role.SUPERVISOR and obj.manager_id == request.user.pk
            )
        if request.user.role == Role.SUPERVISOR:
            return obj.pk == request.user.pk
        return False

    def has_change_permission(self, request, obj=None):
        if not request.user.is_staff:
            return False
        if has_director_access(request.user):
            return True
        if request.user.role == Role.MANAGER:
            if obj is None:
                return True
            return obj.pk == request.user.pk or (
                obj.role == Role.SUPERVISOR and obj.manager_id == request.user.pk
            )
        if request.user.role == Role.SUPERVISOR:
            return obj is not None and obj.pk == request.user.pk
        return False

    def has_add_permission(self, request):
        if not request.user.is_staff:
            return False
        return has_director_access(request.user) or request.user.role == Role.MANAGER

    def has_delete_permission(self, request, obj=None):
        return request.user.is_staff and has_director_access(request.user)

    def save_model(self, request, obj, form, change):
        if request.user.role == Role.MANAGER:
            if not change:
                obj.role = Role.SUPERVISOR
                obj.manager = request.user
                obj.is_staff = True
                obj.is_active = True
            elif obj.manager_id != request.user.pk:
                raise PermissionDenied(
                    "You may only edit supervisors on your team."
                )
            else:
                original = User.objects.get(pk=obj.pk)
                for field in PRIVILEGED_USER_FIELDS:
                    setattr(obj, field, getattr(original, field))
        elif not has_director_access(request.user) and change:
            original = User.objects.get(pk=obj.pk)
            for field in PRIVILEGED_USER_FIELDS:
                setattr(obj, field, getattr(original, field))
        else:
            if obj.role != Role.SUPERVISOR:
                obj.manager = None
            obj.full_clean()
        super().save_model(request, obj, form, change)
