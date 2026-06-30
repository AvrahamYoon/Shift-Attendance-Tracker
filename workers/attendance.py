"""Attendance counting and per-term limit checks."""

from django.core.exceptions import ValidationError
from django.db.models import Count

from workers.models import AttendanceCategory, AttendanceRecord, Term

TERM_ATTENDANCE_LIMITS = {
    AttendanceCategory.ABSENCE: 4,
    AttendanceCategory.TARDY: 4,
    AttendanceCategory.NO_SHOW: 1,
}


def resolve_term_for_date(record_date):
    term = Term.for_date(record_date)
    if term is None:
        raise ValidationError(
            {
                "record_date": (
                    "No BYUI semester covers this date. "
                    "Run: python manage.py sync_byui_terms"
                )
            }
        )
    return term


def attendance_counts_for_term(worker, term):
    """Return {category: count} for one worker in one term."""
    counts = {category.value: 0 for category in AttendanceCategory}
    rows = (
        AttendanceRecord.objects.filter(worker=worker, term=term)
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


def occurrence_number(record):
    """1-based index of this record within worker + term + category."""
    if not record.worker_id or not record.term_id or not record.category:
        return None
    ordering = AttendanceRecord.objects.filter(
        worker_id=record.worker_id,
        term_id=record.term_id,
        category=record.category,
    ).order_by("record_date", "created_at", "pk")
    if record.pk:
        ids = list(ordering.values_list("pk", flat=True))
        if record.pk in ids:
            return ids.index(record.pk) + 1
    return ordering.count() + 1


def occurrence_label(record):
    number = occurrence_number(record)
    if number is None:
        return record.get_category_display()
    return f"{record.get_category_display()} #{number}"


def limit_warnings_for_record(record):
    """Warnings after a record is saved (includes the new record in counts)."""
    if not record.term_id:
        return []
    summary = attendance_summary_for_term(record.worker, record.term)
    info = summary.get(record.category)
    if not info:
        return []
    warnings = []
    n = occurrence_number(record)
    label = info["label"]
    if info["exceeded"]:
        warnings.append(
            f"{record.worker.name} now has {info['count']} {label.lower()} "
            f"this term (limit {info['limit']}). This is #{n}."
        )
    elif info["at_limit"]:
        warnings.append(
            f"{record.worker.name} has reached the term limit for "
            f"{label.lower()} ({info['limit']}/{info['limit']}). This is #{n}."
        )
    return warnings


def limit_warnings_if_added(worker, term, category):
    """Warnings if one more record of this category were added."""
    summary = attendance_summary_for_term(worker, term)
    info = summary[category]
    new_count = info["count"] + 1
    limit = info["limit"]
    label = info["label"]
    if new_count > limit:
        return [
            f"This would be {label.lower()} #{new_count} this term "
            f"(limit {limit}) — over the allowed count."
        ]
    if new_count == limit:
        return [
            f"This would reach the term limit for {label.lower()} "
            f"({limit}/{limit})."
        ]
    return []
