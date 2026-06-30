from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models


class Role(models.TextChoices):
    DIRECTOR = "director", "Director"
    MANAGER = "manager", "Manager"
    SUPERVISOR = "supervisor", "Supervisor"


class User(AbstractUser):
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.SUPERVISOR,
    )
    building = models.ForeignKey(
        "buildings.Building",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="supervisor_users",
        help_text="Required for supervisors — the building they manage.",
    )
    manager = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="supervisors",
        limit_choices_to={"role": Role.MANAGER},
        help_text="Required for supervisors — the manager they report to.",
    )

    class Meta:
        ordering = ["username"]

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    def clean(self):
        super().clean()
        if self.role == Role.SUPERVISOR:
            if not self.building_id:
                raise ValidationError(
                    {"building": "Supervisors must be assigned to a building."}
                )
            if not self.manager_id:
                raise ValidationError(
                    {"manager": "Supervisors must be assigned to a manager."}
                )
            if self.manager and self.manager.role != Role.MANAGER:
                raise ValidationError(
                    {"manager": "Supervisor's manager must have the Manager role."}
                )
        else:
            if self.building_id:
                raise ValidationError(
                    {"building": "Only supervisors may have a building assignment."}
                )
            if self.manager_id:
                raise ValidationError(
                    {"manager": "Only supervisors may have a manager assignment."}
                )
