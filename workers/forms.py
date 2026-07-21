from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone

from config.permissions import filter_buildings, filter_workers, user_can_access_building
from workers.attendance import resolve_term_for_date
from workers.models import AttendanceCategory, AttendanceRecord, Note, Worker, WorkerStatus
from workers.roster import active_workers_queryset, enrollment_for, term_has_roster
from workers.models import Term


def _require_term_for_date(record_date):
    """Validate record_date falls in a BYUI term; re-raise for forms."""
    try:
        return resolve_term_for_date(record_date)
    except ValidationError as exc:
        if hasattr(exc, "message_dict"):
            raise ValidationError(exc.message_dict) from exc
        raise ValidationError({"record_date": exc.messages}) from exc


class BuildingScopedModelForm(forms.ModelForm):
    """Limit building choices to the current user's accessible buildings."""

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        if user is not None and "building" in self.fields:
            from buildings.models import Building

            self.fields["building"].queryset = filter_buildings(
                Building.objects.order_by("name"),
                user,
            )
            self.fields["building"].widget.can_add_related = False
            self.fields["building"].widget.can_change_related = False
            self.fields["building"].widget.can_delete_related = False
            self.fields["building"].widget.can_view_related = False

    def clean_building(self):
        building = self.cleaned_data.get("building")
        if building is None or self.user is None:
            return building
        if not user_can_access_building(self.user, building):
            raise ValidationError(
                "You do not have permission to use this building."
            )
        return building


class WorkerScopedModelForm(BuildingScopedModelForm):
    """Limit worker choices to the current user's accessible workers."""

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        if user is not None and "worker" in self.fields:
            term = Term.current()
            if term_has_roster(term):
                qs = active_workers_queryset(term).select_related("building").order_by(
                    "name"
                )
            else:
                qs = Worker.objects.filter(status=WorkerStatus.ACTIVE).select_related(
                    "building"
                ).order_by("name")
            if self.instance.pk and self.instance.worker_id:
                qs = Worker.objects.filter(
                    Q(status=WorkerStatus.ACTIVE) | Q(pk=self.instance.worker_id)
                ).select_related("building").order_by("name")
            self.fields["worker"].queryset = filter_workers(qs, user)
            self.fields["worker"].widget.can_add_related = False
            self.fields["worker"].widget.can_change_related = False
            self.fields["worker"].widget.can_delete_related = False
            self.fields["worker"].widget.can_view_related = False

    def clean_worker(self):
        worker = self.cleaned_data.get("worker")
        if worker is None:
            return worker
        if self.user is None:
            return worker
        if not filter_workers(Worker.objects.filter(pk=worker.pk), self.user).exists():
            raise ValidationError(
                "You do not have permission to record attendance for this worker."
            )
        return worker


class WorkerForm(BuildingScopedModelForm):
    class Meta:
        model = Worker
        fields = (
            "name",
            "i_number",
            "phone",
            "building",
            "shift",
            "term_status",
            "status",
        )

    def __init__(self, *args, user=None, view_term=None, **kwargs):
        self.view_term = view_term
        super().__init__(*args, user=user, **kwargs)
        if self.instance.pk and view_term and term_has_roster(view_term):
            enrollment = enrollment_for(self.instance, view_term)
            if enrollment:
                self.initial.setdefault("building", enrollment.building_id)
                self.initial.setdefault("shift", enrollment.shift)
                self.initial.setdefault("term_status", enrollment.term_status)
                self.initial.setdefault("status", enrollment.status)


class AttendanceRecordForm(WorkerScopedModelForm):
    class Meta:
        model = AttendanceRecord
        fields = ("worker", "category", "record_date", "record_time")
        widgets = {
            "record_date": forms.DateInput(attrs={"type": "date"}),
            "record_time": forms.TimeInput(attrs={"type": "time"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["record_date"].required = False
        self.fields["record_date"].help_text = "Optional — defaults to today."
        self.fields["record_time"].required = False
        self.fields["record_time"].help_text = (
            "Optional — e.g. arrival time (tardy) or when noted."
        )
        if not self.instance.pk and not self.initial.get("category"):
            self.initial.setdefault("category", AttendanceCategory.ABSENCE)

    def clean_record_date(self):
        value = self.cleaned_data.get("record_date")
        if not value:
            value = timezone.localdate()
        _require_term_for_date(value)
        return value

    def clean(self):
        cleaned = super().clean()
        worker = cleaned.get("worker")
        category = cleaned.get("category")
        record_date = cleaned.get("record_date")
        if (
            worker
            and category == AttendanceCategory.ABSENCE
            and record_date
        ):
            term = _require_term_for_date(record_date)
            duplicate = AttendanceRecord.objects.filter(
                worker=worker,
                term=term,
                category=AttendanceCategory.ABSENCE,
                record_date=record_date,
            )
            if self.instance.pk:
                duplicate = duplicate.exclude(pk=self.instance.pk)
            if duplicate.exists():
                raise ValidationError(
                    {"record_date": "This worker already has an absence on this date."}
                )
        return cleaned

class AbsenceRecordForm(forms.ModelForm):
    class Meta:
        model = AttendanceRecord
        fields = ("record_date", "record_time")
        widgets = {
            "record_date": forms.DateInput(attrs={"type": "date"}),
            "record_time": forms.TimeInput(attrs={"type": "time"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["record_date"].required = False
        self.fields["record_date"].help_text = "One absence per day — duplicates are not counted."
        self.fields["record_time"].required = False
        self.fields["record_time"].help_text = "Optional — e.g. shift start or when noted."
        if not self.instance.pk:
            self.instance.category = AttendanceCategory.ABSENCE

    def clean_record_date(self):
        value = self.cleaned_data.get("record_date")
        if not value:
            value = timezone.localdate()
        term = _require_term_for_date(value)
        worker = self.instance.worker_id or getattr(self.instance.worker, "pk", None)
        if worker:
            duplicate = AttendanceRecord.objects.filter(
                worker_id=worker,
                term_id=term.pk,
                category=AttendanceCategory.ABSENCE,
                record_date=value,
            )
            if self.instance.pk:
                duplicate = duplicate.exclude(pk=self.instance.pk)
            if duplicate.exists():
                raise ValidationError("This worker already has an absence on this date.")
        return value


class NoteForm(BuildingScopedModelForm):
    class Meta:
        model = Note
        fields = ("building", "worker", "content")

    def __init__(self, *args, parent_worker=None, **kwargs):
        self.parent_worker = parent_worker
        super().__init__(*args, **kwargs)
        self.fields["worker"].required = False
        self.fields["worker"].help_text = "Optional — leave blank for a building-level note."
        if parent_worker is not None and not self.instance.pk:
            self.initial.setdefault("building", parent_worker.building_id)
        self._set_worker_queryset()

    def _set_worker_queryset(self):
        building_id = None
        if self.is_bound:
            building_id = self.data.get(self.add_prefix("building")) or self.data.get("building")
        elif self.instance.building_id:
            building_id = self.instance.building_id
        elif self.initial.get("building"):
            building_id = self.initial.get("building")

        qs = Worker.objects.filter(status=WorkerStatus.ACTIVE).select_related(
            "building"
        ).order_by("name")
        if building_id:
            qs = qs.filter(building_id=building_id)
        elif self.parent_worker is not None:
            qs = qs.filter(building_id=self.parent_worker.building_id)
        if self.user is not None:
            qs = filter_workers(qs, self.user)
        self.fields["worker"].queryset = qs
        self.fields["worker"].widget.can_add_related = False
        self.fields["worker"].widget.can_change_related = False
        self.fields["worker"].widget.can_delete_related = False
        self.fields["worker"].widget.can_view_related = False

    def clean_worker(self):
        worker = self.cleaned_data.get("worker")
        if worker is None:
            return worker
        if self.user is None:
            return worker
        if not filter_workers(Worker.objects.filter(pk=worker.pk), self.user).exists():
            raise ValidationError(
                "You do not have permission to add a note for this worker."
            )
        return worker

    def clean(self):
        cleaned = super().clean()
        building = cleaned.get("building")
        worker = cleaned.get("worker")
        if worker and building and worker.building_id != building.id:
            raise ValidationError(
                {"worker": "Worker must belong to the selected building."}
            )
        return cleaned
