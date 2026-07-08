from django.conf import settings
from django.db import models


class Budget(models.Model):
    building = models.OneToOneField(
        "buildings.Building",
        on_delete=models.CASCADE,
        related_name="budget",
        help_text="Headcount quota for this building.",
    )
    allocated_headcount = models.PositiveIntegerField()
    set_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="budgets_set",
        help_text="Manager who last set this quota.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["building"]

    def __str__(self):
        return f"{self.building}: {self.allocated_headcount}"

    @property
    def current_supervisor(self):
        if not self.building_id:
            return None
        return self.building.current_supervisor

    @property
    def actual_headcount(self):
        from workers.models import WorkerStatus

        return self.building.workers.filter(status=WorkerStatus.ACTIVE).count()

    @property
    def headcount_variance(self):
        return self.actual_headcount - self.allocated_headcount
