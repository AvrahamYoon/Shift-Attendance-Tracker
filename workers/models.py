from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class WorkerStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    INACTIVE = "inactive", "Inactive"


class TermStatus(models.TextChoices):
    STAYING = "staying", "Staying"
    LEAVING = "leaving", "Leaving"
    NEW = "new", "New"


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
    )
    supervisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="workers",
        limit_choices_to={"role": "supervisor"},
    )
    position_number = models.CharField("Position #", max_length=10)
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

    def clean(self):
        super().clean()
        if self.supervisor_id and self.building_id:
            if self.supervisor.building_id != self.building_id:
                raise ValidationError(
                    {
                        "supervisor": (
                            "Supervisor must belong to the same building as the worker."
                        )
                    }
                )


class AttendanceCategory(models.TextChoices):
    ABSENCE = "absence", "Absence"
    NO_SHOW = "no_show", "No Show"
    TARDY = "tardy", "Tardy"


class AttendanceSubtype(models.TextChoices):
    ABSENCE_1 = "absence_1", "Absence 1"
    ABSENCE_2 = "absence_2", "Absence 2"
    ABSENCE_3 = "absence_3", "Absence 3"
    ABSENCE_4 = "absence_4", "Absence 4"
    NO_SHOW_1 = "no_show_1", "No Show 1"
    NO_SHOW_2 = "no_show_2", "No Show 2"
    TARDY_1 = "tardy_1", "Tardy 1"
    TARDY_2 = "tardy_2", "Tardy 2"
    TARDY_3 = "tardy_3", "Tardy 3"
    TARDY_4 = "tardy_4", "Tardy 4"
    VERBAL = "verbal", "Verbal"
    WRITTEN = "written", "Written"

CATEGORY_SUBTYPE_MAP = {
    AttendanceCategory.ABSENCE: {
        AttendanceSubtype.ABSENCE_1,
        AttendanceSubtype.ABSENCE_2,
        AttendanceSubtype.ABSENCE_3,
        AttendanceSubtype.ABSENCE_4,
        AttendanceSubtype.VERBAL,
        AttendanceSubtype.WRITTEN,
    },
    AttendanceCategory.NO_SHOW: {
        AttendanceSubtype.NO_SHOW_1,
        AttendanceSubtype.NO_SHOW_2,
        AttendanceSubtype.VERBAL,
        AttendanceSubtype.WRITTEN,
    },
    AttendanceCategory.TARDY: {
        AttendanceSubtype.TARDY_1,
        AttendanceSubtype.TARDY_2,
        AttendanceSubtype.TARDY_3,
        AttendanceSubtype.TARDY_4,
        AttendanceSubtype.VERBAL,
        AttendanceSubtype.WRITTEN,
    },
}


class AttendanceRecord(models.Model):
    worker = models.ForeignKey(
        Worker,
        on_delete=models.CASCADE,
        related_name="attendance_records",
    )
    category = models.CharField(max_length=20, choices=AttendanceCategory.choices)
    subtype = models.CharField(max_length=20, choices=AttendanceSubtype.choices)
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
        return f"{self.worker} — {self.get_category_display()} / {self.get_subtype_display()} ({self.record_date})"

    def clean(self):
        super().clean()
        allowed = CATEGORY_SUBTYPE_MAP.get(self.category, set())
        if self.subtype not in allowed:
            raise ValidationError(
                {
                    "subtype": (
                        f"Subtype '{self.subtype}' is not valid for "
                        f"category '{self.category}'."
                    )
                }
            )


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


def attendance_totals_for_worker(worker, year=None, month=None):
    """Return attendance counts grouped by category and subtype."""
    qs = worker.attendance_records.all()
    if year is not None:
        qs = qs.filter(record_date__year=year)
    if month is not None:
        qs = qs.filter(record_date__month=month)

    totals = {
        AttendanceCategory.ABSENCE: {},
        AttendanceCategory.NO_SHOW: {},
        AttendanceCategory.TARDY: {},
    }
    for category in totals:
        for subtype, _label in AttendanceSubtype.choices:
            if subtype in CATEGORY_SUBTYPE_MAP.get(category, set()):
                count = qs.filter(category=category, subtype=subtype).count()
                if count:
                    totals[category][subtype] = count

    totals["grand_total"] = qs.count()
    return totals
