from django.contrib import admin, messages
from django.utils.html import format_html
from django.utils import timezone
from unfold.admin import ModelAdmin, TabularInline

from accounts.models import Role
from config.admin_mixins import (
    AuditStampAdminMixin,
    InlineAuditStampMixin,
    NoteAdmin,
    RoleFilteredAdminMixin,
    WorkerAdmin,
    WorkerRelatedAdmin,
)
from workers.attendance import (
    attendance_summary_for_term,
    limit_warnings_for_record,
    limit_warnings_if_added,
    occurrence_label,
    resolve_term_for_date,
)
from workers.models import AttendanceCategory, AttendanceRecord, MonthlyScore, Note, Term, Worker


INLINE_AUDIT_FIELDS = {
    AttendanceRecord: "recorded_by",
    Note: "author",
    MonthlyScore: "supervisor",
}


@admin.register(Term)
class TermAdmin(RoleFilteredAdminMixin, ModelAdmin):
    permission_filter = None
    role_permissions = {
        Role.DIRECTOR: ("view", "add", "change", "delete"),
        Role.MANAGER: ("view",),
        Role.SUPERVISOR: ("view",),
    }
    list_display = ("name", "start_date", "end_date", "is_current_display")
    search_fields = ("name",)

    def get_queryset(self, request):
        return Term.objects.all()

    @admin.display(description="Current?")
    def is_current_display(self, obj):
        today = timezone.localdate()
        if obj.start_date <= today <= obj.end_date:
            return "Yes"
        return "—"


class AttendanceRecordInline(InlineAuditStampMixin, TabularInline):
    model = AttendanceRecord
    audit_field = "recorded_by"
    extra = 0
    fields = ("category", "record_date", "occurrence_display", "created_at")
    readonly_fields = ("occurrence_display", "created_at")

    @admin.display(description="#")
    def occurrence_display(self, obj):
        if not obj.pk:
            return "—"
        return occurrence_label(obj)


class NoteInline(InlineAuditStampMixin, TabularInline):
    model = Note
    audit_field = "author"
    extra = 0
    fk_name = "worker"
    fields = ("content", "building", "created_at")
    readonly_fields = ("created_at",)


class MonthlyScoreInline(InlineAuditStampMixin, TabularInline):
    model = MonthlyScore
    audit_field = "supervisor"
    extra = 0
    fields = ("year", "month", "score")


@admin.register(Worker)
class WorkerModelAdmin(WorkerAdmin):
    list_display = (
        "name",
        "i_number",
        "building",
        "position_slot_display",
        "term_attendance_short",
        "status",
        "current_supervisor_display",
    )
    list_filter = ("building", "status", "term_status", "is_lead")
    search_fields = ("name", "i_number", "phone")
    readonly_fields = ("term_attendance_summary",)
    inlines = [AttendanceRecordInline, NoteInline, MonthlyScoreInline]
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    "i_number",
                    "phone",
                    "building",
                    "position_number",
                    "is_lead",
                    "shift",
                    "term_status",
                    "status",
                )
            },
        ),
        (
            "Term attendance",
            {
                "fields": ("term_attendance_summary",),
                "description": (
                    "Counts are automatic per semester. Limits: "
                    "4 absences, 4 tardies, 1 no show."
                ),
            },
        ),
    )

    @admin.display(description="POS #", ordering="position_number")
    def position_slot_display(self, obj):
        lead = "-L" if obj.is_lead else ""
        return f"{obj.position_number}{lead}"

    @admin.display(description="Term attendance")
    def term_attendance_short(self, obj):
        term = Term.current()
        if not term:
            return "—"
        summary = attendance_summary_for_term(obj, term)
        parts = []
        for key in (AttendanceCategory.ABSENCE, AttendanceCategory.TARDY, AttendanceCategory.NO_SHOW):
            info = summary[key.value]
            flag = "!" if info["exceeded"] else ""
            parts.append(f"{info['label'][0]}:{info['count']}/{info['limit']}{flag}")
        return " ".join(parts)

    @admin.display(description="Current term totals")
    def term_attendance_summary(self, obj):
        if not obj.pk:
            return "—"
        term = Term.current()
        if not term:
            return format_html(
                '<p class="text-red-600">No active term for today. Add a term in Admin.</p>'
            )
        summary = attendance_summary_for_term(obj, term)
        rows = []
        for key in (AttendanceCategory.ABSENCE, AttendanceCategory.TARDY, AttendanceCategory.NO_SHOW):
            info = summary[key.value]
            style = "color: #b45309; font-weight: 600;" if info["exceeded"] else ""
            rows.append(
                f"<tr style='{style}'><td>{info['label']}</td>"
                f"<td>{info['count']} / {info['limit']}</td></tr>"
            )
        return format_html(
            "<p><strong>{}</strong></p><table>{}</table>",
            term.name,
            format_html("".join(rows)),
        )

    @admin.display(description="Current supervisor")
    def current_supervisor_display(self, obj):
        supervisor = obj.current_supervisor
        return supervisor.get_full_name() or supervisor.username if supervisor else "—"

    def save_model(self, request, obj, form, change):
        if not change and request.user.role == "supervisor":
            obj.building = request.user.building
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        self._stamp_inline_audit_fields(request, formset)
        super().save_formset(request, form, formset, change)
        if formset.model is AttendanceRecord:
            self._attendance_limit_messages(request, formset)

    def _stamp_inline_audit_fields(self, request, formset):
        audit_field = INLINE_AUDIT_FIELDS.get(formset.model)
        if not audit_field:
            return
        model = formset.model
        for inline_form in formset.forms:
            if not hasattr(inline_form, "instance"):
                continue
            instance = inline_form.instance
            if instance.pk:
                original = model.objects.filter(pk=instance.pk).first()
                if original:
                    setattr(instance, audit_field, getattr(original, audit_field))
            else:
                setattr(instance, audit_field, request.user)
            if (
                model is Note
                and request.user.role == "supervisor"
                and not instance.building_id
            ):
                instance.building = request.user.building

    def _attendance_limit_messages(self, request, formset):
        for inline_form in formset.forms:
            instance = inline_form.instance
            if not instance.pk or not inline_form.has_changed():
                continue
            for warning in limit_warnings_for_record(instance):
                messages.warning(request, warning)

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if request.user.role == "supervisor":
            readonly.append("building")
        return readonly


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(AuditStampAdminMixin, WorkerRelatedAdmin):
    audit_fields = ("recorded_by",)
    list_display = (
        "worker",
        "term",
        "category",
        "occurrence_display",
        "record_date",
        "recorded_by",
        "created_at",
    )
    list_filter = ("category", "term", "record_date", "worker__building")
    search_fields = ("worker__name", "worker__i_number")
    date_hierarchy = "record_date"
    autocomplete_fields = ("worker",)
    readonly_fields = ("term", "occurrence_display", "created_at")

    @admin.display(description="Record")
    def occurrence_display(self, obj):
        return occurrence_label(obj)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.recorded_by = request.user
        if not obj.term_id and obj.record_date:
            obj.term = resolve_term_for_date(obj.record_date)
        if not change and obj.worker_id and obj.term_id and obj.category:
            for warning in limit_warnings_if_added(
                obj.worker, obj.term, obj.category
            ):
                messages.warning(request, warning)
        super().save_model(request, obj, form, change)
        if not change:
            for warning in limit_warnings_for_record(obj):
                messages.warning(request, warning)


@admin.register(Note)
class NoteModelAdmin(AuditStampAdminMixin, NoteAdmin):
    audit_fields = ("author",)
    list_display = ("building", "worker", "author", "created_at", "content_preview")
    list_filter = ("building", "created_at")
    search_fields = ("content", "worker__name", "worker__i_number")
    autocomplete_fields = ("worker",)
    readonly_fields = ("created_at",)

    @admin.display(description="Content")
    def content_preview(self, obj):
        return obj.content[:80] + ("…" if len(obj.content) > 80 else "")

    def save_model(self, request, obj, form, change):
        if request.user.role == "supervisor" and not obj.building_id:
            obj.building = request.user.building
        super().save_model(request, obj, form, change)


@admin.register(MonthlyScore)
class MonthlyScoreAdmin(AuditStampAdminMixin, WorkerRelatedAdmin):
    audit_fields = ("supervisor",)
    list_display = ("worker", "year", "month", "score", "supervisor")
    list_filter = ("year", "month", "worker__building")
    search_fields = ("worker__name", "worker__i_number")
    autocomplete_fields = ("worker",)
