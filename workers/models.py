from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class WorkerStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    INACTIVE = "inactive", "Inactive"


class TermStatus(models.TextChoices):
    STAYING = "staying", "Staying"
    LEAVING = "leaving", "Leaving"
    NEW = "new", "New"


class Term(models.Model):
    """Academic semester used for attendance limits and totals."""

    name = models.CharField(max_length=100, help_text='e.g. "2026 Spring"')
    start_date = models.DateField()
    end_date = models.DateField()

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError({"end_date": "End date must be on or after start date."})

    @classmethod
    def for_date(cls, record_date):
        return (
            cls.objects.filter(start_date__lte=record_date, end_date__gte=record_date)
            .order_by("-start_date")
            .first()
        )

    @classmethod
    def current(cls):
        return cls.for_date(timezone.localdate())


class Worker(models.Model):
    name = models.CharField(max_length=200)
    i_number = models.CharField(
        "I-Number",
        max_length=50,
        unique=True,
        help_text="Student ID, also used as employee identifier.",
    )
    phone = models.CharField(max_length=30, blank=True)
    building = models.ForeignKey(
        "buildings.Building",
        on_delete=models.PROTECT,
        related_name="workers",
        help_text="The building (work site) this position belongs to.",
    )
    position_number = models.CharField(
        "Position slot",
        max_length=10,
        help_text=(
            'Slot number at this building (original spreadsheet "POS #" column). '
            'Examples: "1", "2". Team leads use is_lead (suffix -L in the old sheet).'
        ),
    )
    is_lead = models.BooleanField(
        "Lead",
        default=False,
        help_text="Team lead position (suffix -L in original spreadsheet).",
    )
    shift = models.CharField(
        max_length=50,
        blank=True,
        help_text='e.g. "4:30-7:30 AM"',
    )
    term_status = models.CharField(
        max_length=20,
        choices=TermStatus.choices,
        default=TermStatus.STAYING,
    )
    status = models.CharField(
        max_length=20,
        choices=WorkerStatus.choices,
        default=WorkerStatus.ACTIVE,
    )

    class Meta:
        ordering = ["building", "position_number", "name"]

    def __str__(self):
        lead = "-L" if self.is_lead else ""
        return f"{self.name} ({self.i_number}) — POS {self.position_number}{lead}"

    @property
    def current_supervisor(self):
        if not self.building_id:
            return None
        return self.building.current_supervisor


class AttendanceCategory(models.TextChoices):
    ABSENCE = "absence", "Absence"
    NO_SHOW = "no_show", "No Show"
    TARDY = "tardy", "Tardy"


class AttendanceRecord(models.Model):
    worker = models.ForeignKey(
        Worker,
        on_delete=models.CASCADE,
        related_name="attendance_records",
    )
    term = models.ForeignKey(
        Term,
        on_delete=models.PROTECT,
        related_name="attendance_records",
    )
    category = models.CharField(max_length=20, choices=AttendanceCategory.choices)
    record_date = models.DateField()
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="attendance_records_recorded",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-record_date", "-created_at"]

    def __str__(self):
        from workers.attendance import occurrence_label

        return f"{self.worker} — {occurrence_label(self)} ({self.record_date})"

    def save(self, *args, **kwargs):
        if not self.term_id and self.record_date:
            from workers.attendance import resolve_term_for_date

            self.term = resolve_term_for_date(self.record_date)
        super().save(*args, **kwargs)


class Note(models.Model):
    worker = models.ForeignKey(
        Worker,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="notes",
        help_text="Leave blank for a building-level note.",
    )
    building = models.ForeignKey(
        "buildings.Building",
        on_delete=models.CASCADE,
        related_name="notes",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="notes_authored",
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        target = self.worker or self.building
        return f"Note for {target} ({self.created_at:%Y-%m-%d})"

    def clean(self):
        super().clean()
        if self.worker_id and self.building_id:
            if self.worker.building_id != self.building_id:
                raise ValidationError(
                    {"worker": "Worker must belong to the selected building."}
                )


class MonthlyScore(models.Model):
    worker = models.ForeignKey(
        Worker,
        on_delete=models.CASCADE,
        related_name="monthly_scores",
    )
    year = models.PositiveIntegerField()
    month = models.PositiveIntegerField()
    score = models.DecimalField(max_digits=5, decimal_places=2)
    supervisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="monthly_scores_given",
        verbose_name="scored by",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-year", "-month"]
        constraints = [
            models.UniqueConstraint(
                fields=["worker", "year", "month"],
                name="unique_worker_monthly_score",
            ),
            models.CheckConstraint(
                condition=models.Q(month__gte=1, month__lte=12),
                name="monthly_score_valid_month",
            ),
        ]

    def __str__(self):
        return f"{self.worker} — {self.year}-{self.month:02d}: {self.score}"
