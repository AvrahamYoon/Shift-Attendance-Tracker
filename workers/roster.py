"""Per-term worker roster helpers."""

from workers.models import Term, TermStatus, WorkerStatus

ROSTER_START_TERM_NAME = "Spring 2026"


def roster_start_term():
    return Term.objects.filter(name=ROSTER_START_TERM_NAME).first()


def term_has_roster(term):
    """Rosters apply from Spring 2026 onward; earlier terms stay empty."""
    start = roster_start_term()
    if not start or not term:
        return False
    return term.start_date >= start.start_date


def previous_term(term):
    if not term:
        return None
    return (
        Term.objects.filter(end_date__lt=term.start_date)
        .order_by("-end_date")
        .first()
    )


def inherit_roster_from_previous_term(term):
    """Copy active enrollments from the prior term. No-op before roster epoch."""
    from workers.models import WorkerTermEnrollment

    if not term_has_roster(term):
        return 0
    if WorkerTermEnrollment.objects.filter(term=term).exists():
        return 0

    prior = previous_term(term)
    if not prior or not term_has_roster(prior):
        return 0

    created = 0
    for enrollment in WorkerTermEnrollment.objects.filter(
        term=prior,
        status=WorkerStatus.ACTIVE,
    ).select_related("worker", "building"):
        _, was_created = WorkerTermEnrollment.objects.get_or_create(
            worker=enrollment.worker,
            term=term,
            defaults={
                "building": enrollment.building,
                "shift": enrollment.shift,
                "term_status": TermStatus.STAYING,
                "status": WorkerStatus.ACTIVE,
            },
        )
        if was_created:
            created += 1
    return created


def ensure_all_term_rosters():
    """Fill empty rosters from the previous term (idempotent)."""
    total = 0
    for term in Term.objects.order_by("start_date"):
        if term_has_roster(term):
            total += inherit_roster_from_previous_term(term)
    return total


def sync_worker_enrollment(worker, term, *, building, shift, term_status, status):
    """Keep Worker profile fields and term enrollment aligned."""
    from workers.models import WorkerTermEnrollment

    worker.building = building
    worker.shift = shift
    worker.term_status = term_status
    worker.status = status
    worker.save(
        update_fields=["building", "shift", "term_status", "status"],
    )
    if term_has_roster(term):
        WorkerTermEnrollment.objects.update_or_create(
            worker=worker,
            term=term,
            defaults={
                "building": building,
                "shift": shift,
                "term_status": term_status,
                "status": status,
            },
        )


def enrollment_for(worker, term):
    from workers.models import WorkerTermEnrollment

    if not worker or not term or not term_has_roster(term):
        return None
    return WorkerTermEnrollment.objects.filter(worker=worker, term=term).first()


def active_workers_queryset(term):
    from workers.models import Worker, WorkerTermEnrollment

    if not term_has_roster(term):
        return Worker.objects.none()
    return Worker.objects.filter(
        term_enrollments__term=term,
        term_enrollments__status=WorkerStatus.ACTIVE,
    ).distinct()


def active_enrollment_count_for_building(building, term):
    from workers.models import WorkerTermEnrollment

    if not term_has_roster(term):
        return building.workers.filter(status=WorkerStatus.ACTIVE).count()
    return WorkerTermEnrollment.objects.filter(
        term=term,
        building=building,
        status=WorkerStatus.ACTIVE,
    ).count()
