"""Attendance counting and per-term limit checks."""

from django.core.exceptions import ValidationError
from django.db.models import Count
from django.utils import timezone

from workers.models import AttendanceCategory, AttendanceRecord, Term

TERM_ATTENDANCE_LIMITS = {
    AttendanceCategory.ABSENCE: 4,
    AttendanceCategory.TARDY: 4,
    AttendanceCategory.NO_SHOW: 1,
}

DISPLAY_CATEGORIES = (
    AttendanceCategory.ABSENCE,
    AttendanceCategory.TARDY,
    AttendanceCategory.NO_SHOW,
)

ABSENCE_CATEGORY = AttendanceCategory.ABSENCE


def summary_overall_status(summary):
    """'over' | 'at_limit' | 'ok' for display highlighting."""
    if any(summary[category.value]["exceeded"] for category in DISPLAY_CATEGORIES):
        return "over"
    if any(summary[category.value]["at_limit"] for category in DISPLAY_CATEGORIES):
        return "at_limit"
    return "ok"


def resolve_term_for_date(record_date):
    """Resolve term for a date; gaps between semesters use the previous term."""
    term = Term.for_date(record_date)
    if term is None:
        raise ValidationError(
            {
                "record_date": (
                    "No BYUI semester is available for this date "
                    "(before the earliest synced term). "
                    "Run: python manage.py sync_byui_terms"
                )
            }
        )
    return term


def absence_days_for_term(worker, term):
    """Distinct absence dates for one worker in one term."""
    return (
        AttendanceRecord.objects.filter(
            worker=worker,
            term=term,
            category=ABSENCE_CATEGORY,
        )
        .values("record_date")
        .distinct()
        .count()
    )


def attendance_counts_for_term(worker, term):
    """Return {category: count} for one worker in one term."""
    counts = {category.value: 0 for category in AttendanceCategory}
    base_qs = AttendanceRecord.objects.filter(worker=worker, term=term)
    counts[ABSENCE_CATEGORY.value] = absence_days_for_term(worker, term)
    rows = (
        base_qs.exclude(category=ABSENCE_CATEGORY)
        .values("category")
        .annotate(total=Count("id"))
    )
    for row in rows:
        counts[row["category"]] = row["total"]
    return counts


def attendance_summary_for_term(worker, term):
    """Counts plus limits and exceeded flags for display / warnings."""
    counts = attendance_counts_for_term(worker, term)
    summary = {}
    for category in AttendanceCategory:
        count = counts.get(category.value, 0)
        limit = TERM_ATTENDANCE_LIMITS[category]
        summary[category.value] = {
            "label": category.label,
            "count": count,
            "limit": limit,
            "exceeded": count > limit,
            "at_limit": count >= limit,
        }
    return summary


def absence_day_number(record):
    """1-based index of this absence date within worker + term."""
    if (
        not record.worker_id
        or not record.term_id
        or record.category != ABSENCE_CATEGORY
        or not record.record_date
    ):
        return None
    dates = sorted(
        AttendanceRecord.objects.filter(
            worker_id=record.worker_id,
            term_id=record.term_id,
            category=ABSENCE_CATEGORY,
        )
        .values_list("record_date", flat=True)
        .distinct()
    )
    if record.record_date in dates:
        return dates.index(record.record_date) + 1
    return len(dates) + 1


def occurrence_number(record):
    """1-based index of this record within worker + term + category."""
    if record.category == ABSENCE_CATEGORY:
        return absence_day_number(record)
    if not record.worker_id or not record.term_id or not record.category:
        return None
    ordering = AttendanceRecord.objects.filter(
        worker_id=record.worker_id,
        term_id=record.term_id,
        category=record.category,
    ).order_by("record_date", "record_time", "created_at", "pk")
    if record.pk:
        ids = list(ordering.values_list("pk", flat=True))
        if record.pk in ids:
            return ids.index(record.pk) + 1
    return ordering.count() + 1


def _format_record_time(record_time):
    if not record_time:
        return ""
    hour = record_time.strftime("%I").lstrip("0") or "12"
    return f" at {hour}:{record_time.strftime('%M %p')}"


def occurrence_label(record):
    number = occurrence_number(record)
    time_part = _format_record_time(record.record_time)

    if record.category == ABSENCE_CATEGORY and record.record_date:
        if number is None:
            return f"{record.get_category_display()} ({record.record_date}{time_part})"
        return f"Absence day {number} ({record.record_date}{time_part})"
    if number is None:
        if record.record_date:
            return f"{record.get_category_display()} ({record.record_date}{time_part})"
        return record.get_category_display()
    date_part = f" — {record.record_date}" if record.record_date else ""
    return f"{record.get_category_display()} #{number}{date_part}{time_part}"


def projected_count_after_add(worker, term, category, record_date=None):
    """Count after adding one record (absence uses distinct days)."""
    record_date = record_date or timezone.localdate()
    if category == ABSENCE_CATEGORY:
        existing_dates = set(
            AttendanceRecord.objects.filter(
                worker=worker,
                term=term,
                category=ABSENCE_CATEGORY,
            ).values_list("record_date", flat=True)
        )
        existing_dates.add(record_date)
        return len(existing_dates)
    return attendance_counts_for_term(worker, term)[category] + 1


def limit_warnings_for_record(record):
    """Warnings after a record is saved (includes the new record in counts)."""
    if not record.term_id:
        return []
    summary = attendance_summary_for_term(record.worker, record.term)
    info = summary.get(record.category)
    if not info:
        return []
    n = occurrence_number(record)
    label = info["label"]
    if record.category == ABSENCE_CATEGORY:
        detail = f"absence day {n} ({record.record_date})"
    else:
        detail = f"#{n}"
    if info["exceeded"]:
        return [
            (
                "error",
                f"{record.worker.name} now has {info['count']} {label.lower()} "
                f"this term (limit {info['limit']}). This is {detail} — OVER LIMIT.",
            )
        ]
    if info["at_limit"]:
        return [
            (
                "warning",
                f"{record.worker.name} has reached the term limit for "
                f"{label.lower()} ({info['limit']}/{info['limit']}). This is {detail}.",
            )
        ]
    return []


def limit_warnings_if_added(worker, term, category, record_date=None):
    """Warnings if one more record of this category were added."""
    summary = attendance_summary_for_term(worker, term)
    info = summary[category]
    new_count = projected_count_after_add(worker, term, category, record_date)
    if new_count == info["count"]:
        return []
    limit = info["limit"]
    label = info["label"]
    if new_count > limit:
        return [
            (
                "error",
                f"This would be {label.lower()} #{new_count} this term "
                f"(limit {limit}) — OVER the allowed count.",
            )
        ]
    if new_count == limit:
        return [
            (
                "warning",
                f"This would reach the term limit for {label.lower()} "
                f"({limit}/{limit}).",
            )
        ]
    return []
