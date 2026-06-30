from django.core.exceptions import PermissionDenied
from django.db import transaction

from config.permissions import filter_by_worker_relation, filter_notes, filter_workers
from workers.attendance import (
    limit_warnings_for_record,
    limit_warnings_if_added,
    resolve_term_for_date,
)
from workers.models import AttendanceRecord, MonthlyScore, Note, Worker


def workers_for_user(user):
    return filter_workers(Worker.objects.select_related("building"), user)


def get_worker_for_user(user, worker_id):
    worker = workers_for_user(user).filter(pk=worker_id).first()
    if worker is None:
        raise PermissionDenied
    return worker


def notes_for_user(user, worker=None):
    qs = filter_notes(Note.objects.select_related("author", "worker"), user)
    if worker is not None:
        qs = qs.filter(worker=worker)
    return qs


def attendance_for_user(user, worker=None):
    qs = filter_by_worker_relation(
        AttendanceRecord.objects.select_related("recorded_by", "worker", "term"),
        user,
    )
    if worker is not None:
        qs = qs.filter(worker=worker)
    return qs


def scores_for_user(user, worker=None):
    qs = filter_by_worker_relation(
        MonthlyScore.objects.select_related("supervisor", "worker"),
        user,
    )
    if worker is not None:
        qs = qs.filter(worker=worker)
    return qs


@transaction.atomic
def save_worker_for_user(user, worker, *, is_new=False):
    if user.role == "supervisor":
        worker.building = user.building
    elif is_new:
        raise PermissionDenied
    worker.full_clean()
    worker.save()
    return worker


@transaction.atomic
def create_attendance_record(user, worker, category, record_date=None):
    from django.utils import timezone

    get_worker_for_user(user, worker.pk)
    if not record_date:
        record_date = timezone.localdate()
    term = resolve_term_for_date(record_date)
    record = AttendanceRecord(
        worker=worker,
        term=term,
        category=category,
        record_date=record_date,
        recorded_by=user,
    )
    record.full_clean()
    record.save()
    return record, limit_warnings_for_record(record)


@transaction.atomic
def create_note(user, building, content, worker=None):
    if user.role == "supervisor":
        if building.id != user.building_id:
            raise PermissionDenied
        if worker and worker.building_id != user.building_id:
            raise PermissionDenied
    note = Note(
        worker=worker,
        building=building,
        content=content,
        author=user,
    )
    note.full_clean()
    note.save()
    return note


@transaction.atomic
def save_monthly_score(user, worker, year, month, score):
    get_worker_for_user(user, worker.pk)
    record, _created = MonthlyScore.objects.update_or_create(
        worker=worker,
        year=year,
        month=month,
        defaults={"score": score, "supervisor": user},
    )
    record.full_clean()
    record.save()
    return record
