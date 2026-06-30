from django.db import models


class Building(models.Model):
    name = models.CharField(max_length=200)
    address = models.TextField(blank=True)

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
        from accounts.models import Role

        return self.supervisor_users.filter(role=Role.SUPERVISOR).first()
