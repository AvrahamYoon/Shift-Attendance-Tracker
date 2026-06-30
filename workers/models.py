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

    name = models.CharField(
        max_length=100,
        help_text='BYUI full semester name, e.g. "Spring 2026".',
    )
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
        help_text="Work site / department this student employee is assigned to.",
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
        ordering = ["building", "name"]

    def __str__(self):
        return f"{self.name} ({self.i_number})"

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
    record_date = models.DateField(
        blank=True,
        help_text="Leave blank when recording — defaults to today (Mountain Time).",
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="attendance_records_recorded",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-record_date", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["worker", "term", "record_date"],
                condition=models.Q(category=AttendanceCategory.ABSENCE),
                name="unique_absence_day_per_worker_term",
            ),
        ]

    def clean(self):
        super().clean()
        if (
            self.category == AttendanceCategory.ABSENCE
            and self.worker_id
            and self.term_id
            and self.record_date
        ):
            duplicate = AttendanceRecord.objects.filter(
                worker_id=self.worker_id,
                term_id=self.term_id,
                category=AttendanceCategory.ABSENCE,
                record_date=self.record_date,
            )
            if self.pk:
                duplicate = duplicate.exclude(pk=self.pk)
            if duplicate.exists():
                raise ValidationError(
                    {"record_date": "This worker already has an absence on this date."}
                )

    def __str__(self):
        from workers.attendance import occurrence_label

        return f"{self.worker} — {occurrence_label(self)} ({self.record_date})"

    def save(self, *args, **kwargs):
        if not self.record_date:
            self.record_date = timezone.localdate()
        if not self.term_id:
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
