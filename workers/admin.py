from django.contrib import admin, messages
from django.utils.html import format_html
from django.utils.safestring import mark_safe
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
    DISPLAY_CATEGORIES,
    attendance_summary_for_term,
    limit_warnings_for_record,
    limit_warnings_if_added,
    occurrence_label,
    resolve_term_for_date,
    summary_overall_status,
)
from workers.forms import AttendanceRecordForm
from workers.models import AttendanceCategory, AttendanceRecord, MonthlyScore, Note, Term, Worker

INLINE_AUDIT_FIELDS = {
    AttendanceRecord: "recorded_by",
    Note: "author",
    MonthlyScore: "supervisor",
}


def _dispatch_limit_message(request, level, text):
    if level == "error":
        messages.error(request, text)
    else:
        messages.warning(request, text)


def _term_summary_for_worker(obj):
    term = Term.current()
    if not term:
        return None
    return attendance_summary_for_term(obj, term)


def _attendance_count_html(info):
    count = info["count"]
    limit = info["limit"]
    base = (
        "display:inline-block;padding:0.2rem 0.45rem;border-radius:4px;"
        "font-weight:600;font-size:0.85rem;white-space:nowrap;"
    )
    if info["exceeded"]:
        return format_html(
            '<span class="attendance-badge attendance-badge--over" '
            'style="{}background:#fecaca;color:#991b1b;">'
            "{}/{}</span>",
            base,
            count,
            limit,
        )
    if info["at_limit"]:
        return format_html(
            '<span class="attendance-badge attendance-badge--at-limit" '
            'style="{}background:#fef08a;color:#854d0e;">'
            "{}/{}</span>",
            base,
            count,
            limit,
        )
    if count > limit / 2:
        return format_html(
            '<span class="attendance-badge attendance-badge--over-half" '
            'style="{}background:#fed7aa;color:#9a3412;">'
            "{}/{}</span>",
            base,
            count,
            limit,
        )
    return format_html(
        '<span class="attendance-badge attendance-badge--ok" '
        'style="{}background:#bbf7d0;color:#166534;">'
        "{}/{}</span>",
        base,
        count,
        limit,
    )


def _attendance_limit_cell_html(summary, category_value):
    return _attendance_count_html(summary[category_value])


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
    form = AttendanceRecordForm
    audit_field = "recorded_by"
    extra = 1
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
    class Media:
        css = {"all": ("css/custom.css",)}

    list_display = (
        "limit_alert",
        "name",
        "i_number",
        "building",
        "shift",
        "term_absences",
        "term_tardies",
        "term_no_shows",
        "status",
        "current_supervisor_display",
    )
    list_filter = ("building", "status", "term_status")
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
                    "Automatic counts for the current BYUI semester. Limits: "
                    "4 absences, 4 tardies, 1 no show."
                ),
            },
        ),
    )

    @admin.display(description="Alert")
    def limit_alert(self, obj):
        term = Term.current()
        if not term:
            return ""
        status = summary_overall_status(attendance_summary_for_term(obj, term))
        if status == "over":
            return mark_safe(
                '<span class="worker-over-limit-flag" '
                'style="display:inline-block;background:#dc2626;color:#fff;'
                "font-weight:800;padding:0.3rem 0.55rem;border-radius:6px;"
                'font-size:0.7rem;letter-spacing:0.04em;text-transform:uppercase;'
                'white-space:nowrap;">Over limit</span>'
            )
        if status == "at_limit":
            return mark_safe(
                '<span class="worker-at-limit-flag" '
                'style="display:inline-block;background:#fef3c7;color:#92400e;'
                "font-weight:700;padding:0.25rem 0.5rem;border-radius:6px;"
                'font-size:0.7rem;letter-spacing:0.03em;text-transform:uppercase;'
                'white-space:nowrap;">At limit</span>'
            )
        return ""

    @admin.display(description="Absences")
    def term_absences(self, obj):
        summary = _term_summary_for_worker(obj)
        if summary is None:
            return "—"
        return _attendance_count_html(summary[AttendanceCategory.ABSENCE.value])

    @admin.display(description="Tardy")
    def term_tardies(self, obj):
        summary = _term_summary_for_worker(obj)
        if summary is None:
            return "—"
        return _attendance_count_html(summary[AttendanceCategory.TARDY.value])

    @admin.display(description="No show")
    def term_no_shows(self, obj):
        summary = _term_summary_for_worker(obj)
        if summary is None:
            return "—"
        return _attendance_count_html(summary[AttendanceCategory.NO_SHOW.value])

    @admin.display(description="Current term totals")
    def term_attendance_summary(self, obj):
        if not obj.pk:
            return "—"
        term = Term.current()
        if not term:
            return mark_safe(
                "<p>No BYUI semester covers today. "
                "Run <code>python manage.py sync_byui_terms</code>.</p>"
            )
        summary = attendance_summary_for_term(obj, term)
        status = summary_overall_status(summary)
        alert_html = ""
        if status == "over":
            exceeded = [
                summary[category.value]["label"]
                for category in DISPLAY_CATEGORIES
                if summary[category.value]["exceeded"]
            ]
            alert_html = format_html(
                '<div class="attendance-alert-over">'
                "Over term limit: {}. Review attendance below."
                "</div>",
                ", ".join(exceeded),
            )
        elif status == "at_limit":
            alert_html = mark_safe(
                '<div class="attendance-alert-at-limit">'
                "At least one category is at the term limit (no room left)."
                "</div>"
            )

        rows = []
        for category in DISPLAY_CATEGORIES:
            info = summary[category.value]
            if info["exceeded"]:
                row_class = "attendance-summary-row--over"
            elif info["at_limit"]:
                row_class = "attendance-summary-row--at-limit"
            elif info["count"] > info["limit"] / 2:
                row_class = "attendance-summary-row--over-half"
            else:
                row_class = ""
            rows.append(
                format_html(
                    "<tr class='{}'><td>{}</td><td>{}</td></tr>",
                    row_class,
                    info["label"],
                    _attendance_count_html(info),
                )
            )
        return format_html(
            "{}" "<p><strong>{}</strong> ({} – {})</p>"
            "<table class='attendance-summary-table'>"
            "<thead><tr><th>Category</th><th>Count</th></tr></thead>"
            "<tbody>{}</tbody></table>",
            mark_safe(alert_html),
            term.name,
            term.start_date,
            term.end_date,
            mark_safe("".join(str(row) for row in rows)),
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
            for level, text in limit_warnings_for_record(instance):
                _dispatch_limit_message(request, level, text)

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if request.user.role == "supervisor":
            readonly.append("building")
        return readonly


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(AuditStampAdminMixin, WorkerRelatedAdmin):
    form = AttendanceRecordForm
    audit_fields = ("recorded_by",)
    list_display = (
        "worker",
        "term",
        "category",
        "term_limit_status",
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

    @admin.display(description="Term limit")
    def term_limit_status(self, obj):
        if not obj.worker_id or not obj.term_id or not obj.category:
            return "—"
        summary = attendance_summary_for_term(obj.worker, obj.term)
        return _attendance_limit_cell_html(summary, obj.category)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.recorded_by = request.user
        if not change and obj.worker_id and obj.category:
            record_date = obj.record_date or timezone.localdate()
            try:
                term = obj.term or resolve_term_for_date(record_date)
            except Exception:
                term = None
            if term:
                for level, text in limit_warnings_if_added(
                    obj.worker, term, obj.category
                ):
                    _dispatch_limit_message(request, level, text)
        super().save_model(request, obj, form, change)
        if not change:
            for level, text in limit_warnings_for_record(obj):
                _dispatch_limit_message(request, level, text)


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
