from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from accounts.models import Role, User
from config.permissions import has_director_access


class DirectorUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "role",
            "manager",
            "is_staff",
            "is_active",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].choices = [
            (Role.MANAGER, Role.MANAGER.label),
            (Role.SUPERVISOR, Role.SUPERVISOR.label),
            (Role.DIRECTOR, Role.DIRECTOR.label),
        ]
        self.fields["manager"].required = False
        self.fields["manager"].queryset = User.objects.filter(
            role=Role.MANAGER
        ).order_by("username")
        self.fields["manager"].help_text = (
            "Required when role is Supervisor — pick the manager they report to."
        )

    def clean(self):
        cleaned = super().clean()
        role = cleaned.get("role")
        manager = cleaned.get("manager")
        if role == Role.SUPERVISOR and not manager:
            raise forms.ValidationError(
                {"manager": "Supervisors must be assigned to a manager."}
            )
        if role != Role.SUPERVISOR and manager:
            raise forms.ValidationError(
                {"manager": "Only supervisors may have a manager assignment."}
            )
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        if user.role != Role.SUPERVISOR:
            user.manager = None
        if commit:
            user.save()
        return user


class ManagerSupervisorCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email")

    def __init__(self, *args, manager_user=None, **kwargs):
        self.manager_user = manager_user
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = Role.SUPERVISOR
        user.manager = self.manager_user
        user.is_staff = True
        user.is_active = True
        if commit:
            user.save()
        return user


class ScopedUserChangeForm(UserChangeForm):
    def clean(self):
        cleaned = super().clean()
        role = cleaned.get("role", self.instance.role)
        manager = cleaned.get("manager", self.instance.manager)
        self.instance.role = role
        self.instance.manager = manager
        self.instance.full_clean()
        return cleaned
