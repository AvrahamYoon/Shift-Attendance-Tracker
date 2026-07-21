"""BYU-Idaho full-semester dates from the official academic calendar.

Source: https://www.byui.edu/academic-calendar/
Classes begin through semester officially ends (testing days included).
"""

from datetime import date

BYUI_FULL_SEMESTERS = (
    {
        "name": "Fall 2025",
        "start_date": date(2025, 9, 15),
        "end_date": date(2025, 12, 17),
    },
    {
        "name": "Winter 2026",
        "start_date": date(2026, 1, 7),
        "end_date": date(2026, 4, 9),
    },
    {
        "name": "Spring 2026",
        "start_date": date(2026, 4, 20),
        "end_date": date(2026, 7, 22),
    },
    {
        "name": "Summer 2026",
        "start_date": date(2026, 7, 27),
        "end_date": date(2026, 9, 9),
    },
    {
        "name": "Fall 2026",
        "start_date": date(2026, 9, 14),
        "end_date": date(2026, 12, 16),
    },
    {
        "name": "Winter 2027",
        "start_date": date(2027, 1, 6),
        "end_date": date(2027, 4, 9),
    },
    {
        "name": "Spring 2027",
        "start_date": date(2027, 4, 19),
        "end_date": date(2027, 7, 21),
    },
)


def sync_byui_terms(Term):
    """Create or update BYUI semester rows. Returns number of terms created."""
    from workers.models import AttendanceRecord

    legacy_names = {
        "2026 Spring": "Spring 2026",
    }
    for old_name, new_name in legacy_names.items():
        old_term = Term.objects.filter(name=old_name).first()
        new_term = Term.objects.filter(name=new_name).first()
        if old_term and new_term:
            AttendanceRecord.objects.filter(term=old_term).update(term=new_term)
            old_term.delete()

    created = 0
    inherited = 0
    for entry in BYUI_FULL_SEMESTERS:
        term, was_created = Term.objects.update_or_create(
            name=entry["name"],
            defaults={
                "start_date": entry["start_date"],
                "end_date": entry["end_date"],
            },
        )
        if was_created:
            created += 1
    from workers.roster import ensure_all_term_rosters

    inherited = ensure_all_term_rosters()
    return created, inherited
