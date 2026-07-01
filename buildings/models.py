from django.conf import settings
from django.db import models


class Building(models.Model):
    name = models.CharField(max_length=200)
    address = models.TextField(blank=True)
    supervisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="supervised_buildings",
        limit_choices_to={"role": "supervisor"},
        help_text="The one supervisor responsible for this building.",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def active_headcount(self):
        from workers.models import WorkerStatus

        return self.workers.filter(status=WorkerStatus.ACTIVE).count()

    @property
    def current_supervisor(self):
        return self.supervisor
