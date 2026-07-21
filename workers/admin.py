from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils import timezone
from unfold.admin import ModelAdmin, TabularInline

from accounts.models import Role
from budget.models import Budget
from config.admin_mixins import (
    AuditStampAdminMixin,
    DeleteDockAdminMixin,
    FULL_ACCESS,
    InlineAuditStampMixin,
    NoteAdmin,
    RoleFilteredAdminMixin,
    VIEW_ONLY,
    WorkerAdmin,
    WorkerRelatedAdmin,
)
from config.permissions import (
    filter_budgets,
    filter_buildings,
    filter_workers,
    has_director_access,
    user_can_access_building,
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
from workers.forms import AbsenceRecordForm, AttendanceRecordForm, NoteForm, WorkerForm
from workers.models import AttendanceCategory, AttendanceRecord, MonthlyScore, Note, Term, Worker
from workers.pdf_reports import (
    build_term_attendance_pdf,
    build_worker_pdf,
    pdf_http_response,
    safe_filename,
)

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
    if info["exceeded"]:
        css = "attendance-badge attendance-badge--over"
    elif info["at_limit"]:
        css = "attendance-badge attendance-badge--at-limit"
    elif count > limit / 2:
        css = "attendance-badge attendance-badge--over-half"
    else:
        css = "attendance-badge attendance-badge--ok"
    return format_html('<span class="{}">{}/{}</span>', css, count, limit)


def _attendance_limit_cell_html(summary, category_value):
    return _attendance_count_html(summary[category_value])


class AttendanceInlineMixin:
    def get_fields(self, request, obj=None):
        fields = list(super().get_fields(request, obj))
        record_admin = self.admin_site._registry[AttendanceRecord]
        if not record_admin.has_delete_permission(request):
            fields = [field for field in fields if field != "inline_delete_link"]
        return fields


@admin.register(Term)
class TermAdmin(DeleteDockAdminMixin, RoleFilteredAdminMixin, ModelAdmin):
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


class AbsenceRecordInline(AttendanceInlineMixin, InlineAuditStampMixin, TabularInline):
    model = AttendanceRecord
    form = AbsenceRecordForm
    audit_field = "recorded_by"
    verbose_name = "Absence day"
    verbose_name_plural = "Absence days"
    extra = 1
    can_delete = False
    fields = ("record_date", "record_time", "occurrence_display", "inline_delete_link", "created_at")
    readonly_fields = ("occurrence_display", "inline_delete_link", "created_at")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(category=AttendanceCategory.ABSENCE)

    @admin.display(description="When")
    def occurrence_display(self, obj):
        if not obj.pk:
            return "—"
        return occurrence_label(obj)

    @admin.display(description="")
    def inline_delete_link(self, obj):
        if not obj.pk:
            return ""
        url = reverse("admin:workers_attendancerecord_delete", args=[obj.pk])
        return format_html(
            '<a href="{}" class="inline-delete-link">Delete</a>',
            url,
        )


class TardyNoShowRecordInline(AttendanceInlineMixin, InlineAuditStampMixin, TabularInline):
    model = AttendanceRecord
    form = AttendanceRecordForm
    audit_field = "recorded_by"
    verbose_name = "Tardy / No show"
    verbose_name_plural = "Tardy / No show"
    extra = 0
    can_delete = False
    fields = ("category", "record_date", "record_time", "occurrence_display", "inline_delete_link", "created_at")
    readonly_fields = ("occurrence_display", "inline_delete_link", "created_at")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.exclude(category=AttendanceCategory.ABSENCE)

    @admin.display(description="When")
    def occurrence_display(self, obj):
        if not obj.pk:
            return "—"
        return occurrence_label(obj)

    @admin.display(description="")
    def inline_delete_link(self, obj):
        if not obj.pk:
            return ""
        url = reverse("admin:workers_attendancerecord_delete", args=[obj.pk])
        return format_html(
            '<a href="{}" class="inline-delete-link">Delete</a>',
            url,
        )


class AttendanceRecordInline(TardyNoShowRecordInline):
    """Backward-compatible alias."""


class NoteInline(InlineAuditStampMixin, TabularInline):
    model = Note
    form = NoteForm
    audit_field = "author"
    extra = 0
    fk_name = "worker"
    fields = ("building", "content", "created_at")
    readonly_fields = ("created_at",)

    def get_formset(self, request, obj=None, **kwargs):
        user = request.user
        parent_worker = obj

        class InlineNoteForm(NoteForm):
            def __init__(self, *args, **kw):
                super().__init__(*args, user=user, parent_worker=parent_worker, **kw)

        kwargs["form"] = InlineNoteForm
        return super().get_formset(request, obj, **kwargs)


class MonthlyScoreInline(InlineAuditStampMixin, TabularInline):
    model = MonthlyScore
    audit_field = "supervisor"
    extra = 0
    fields = ("year", "month", "score")


def _term_for_pdf_export(request):
    term_id = request.GET.get("term")
    if term_id:
        return Term.objects.filter(pk=term_id).first()
    return Term.current()


def _export_pdf_url(name, request, *args):
    url = reverse(name, args=args, current_app=admin.site.name)
    term = _term_for_pdf_export(request)
    if term:
        return f"{url}?term={term.pk}"
    return url


@admin.register(Worker)
class WorkerModelAdmin(DeleteDockAdminMixin, WorkerAdmin):
    form = WorkerForm

    class Media:
        css = {"all": ("css/custom.css",)}
        js = ("admin/js/actions.js", "js/bulk-delete-dock.js")

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
    inlines = [AbsenceRecordInline, TardyNoShowRecordInline, NoteInline, MonthlyScoreInline]
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
                    "4 absence days, 4 tardies, 1 no show. "
                    "Absences count by day (one per date)."
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
            return mark_safe('<span class="worker-over-limit-flag">Over limit</span>')
        if status == "at_limit":
            return mark_safe('<span class="worker-at-limit-flag">At limit</span>')
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

    def get_urls(self):
        urls = super().get_urls()
        info = self.model._meta.app_label, self.model._meta.model_name
        custom_urls = [
            path(
                "export-term-pdf/",
                self.admin_site.admin_view(self.export_term_pdf_view),
                name=f"{info[0]}_{info[1]}_export_term_pdf",
            ),
            path(
                "<path:object_id>/export-pdf/",
                self.admin_site.admin_view(self.export_worker_pdf_view),
                name=f"{info[0]}_{info[1]}_export_pdf",
            ),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["export_term_pdf_url"] = _export_pdf_url(
            "admin:workers_worker_export_term_pdf",
            request,
        )
        return super().changelist_view(request, extra_context)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        if object_id and self.get_queryset(request).filter(pk=object_id).exists():
            extra_context["export_worker_pdf_url"] = _export_pdf_url(
                "admin:workers_worker_export_pdf",
                request,
                object_id,
            )
        return super().change_view(request, object_id, form_url, extra_context)

    def export_term_pdf_view(self, request):
        term = _term_for_pdf_export(request)
        if not term:
            messages.error(request, "No BYUI term is available for export.")
            return redirect("admin:workers_worker_changelist")

        workers = self.get_queryset(request)
        building_id = request.GET.get("building__id__exact")
        if building_id:
            workers = workers.filter(building_id=building_id)
        status = request.GET.get("status__exact")
        if status:
            workers = workers.filter(status=status)

        include_budget = has_director_access(request.user) or request.user.role in (
            Role.MANAGER,
            Role.SUPERVISOR,
        )
        budgets = filter_budgets(Budget.objects.all(), request.user) if include_budget else None
        pdf_bytes = build_term_attendance_pdf(
            workers,
            term,
            request.user,
            budgets=budgets,
        )
        filename = f"attendance-{safe_filename(term.name)}.pdf"
        return pdf_http_response(filename, pdf_bytes)

    def export_worker_pdf_view(self, request, object_id):
        worker = self.get_queryset(request).filter(pk=object_id).first()
        if not worker:
            messages.error(request, "Worker not found or not permitted.")
            return redirect("admin:workers_worker_changelist")

        term = _term_for_pdf_export(request)
        if not term:
            messages.error(request, "No BYUI term is available for export.")
            return redirect("admin:workers_worker_change", object_id)

        pdf_bytes = build_worker_pdf(worker, term, request.user)
        filename = (
            f"worker-{safe_filename(worker.name)}-{safe_filename(term.name)}.pdf"
        )
        return pdf_http_response(filename, pdf_bytes)

    def save_model(self, request, obj, form, change):
        if request.user.role == Role.SUPERVISOR:
            if not user_can_access_building(request.user, obj.building):
                raise PermissionDenied(
                    "You do not have permission to assign workers to this building."
                )
            if change:
                original = Worker.objects.filter(pk=obj.pk).first()
                if original and not user_can_access_building(
                    request.user, original.building
                ):
                    raise PermissionDenied(
                        "You do not have permission to edit this worker."
                    )
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

    def _attendance_limit_messages(self, request, formset):
        for inline_form in formset.forms:
            instance = inline_form.instance
            if not instance.pk or not inline_form.has_changed():
                continue
            for level, text in limit_warnings_for_record(instance):
                _dispatch_limit_message(request, level, text)

    def get_readonly_fields(self, request, obj=None):
        return list(super().get_readonly_fields(request, obj))

    def get_form(self, request, obj=None, **kwargs):
        user = request.user

        class RequestWorkerForm(WorkerForm):
            def __init__(self, *args, **kw):
                super().__init__(*args, user=user, **kw)

        kwargs["form"] = RequestWorkerForm
        return super().get_form(request, obj, **kwargs)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "building":
            from buildings.models import Building

            kwargs["queryset"] = filter_buildings(
                Building.objects.order_by("name"),
                request.user,
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(DeleteDockAdminMixin, AuditStampAdminMixin, WorkerRelatedAdmin):
    role_permissions = {
        Role.DIRECTOR: FULL_ACCESS,
        Role.MANAGER: VIEW_ONLY,
        Role.SUPERVISOR: ("view", "add", "change", "delete"),
    }
    form = AttendanceRecordForm
    audit_fields = ("recorded_by",)
    fields = ("worker", "category", "record_date", "record_time")
    add_fieldsets = (
        (
            None,
            {
                "fields": ("worker", "category", "record_date", "record_time"),
                "description": (
                    "Select the student employee first. Absences count by day "
                    "(one record per date). Add a time for tardies or optional "
                    "absence notes."
                ),
            },
        ),
    )
    list_display = (
        "worker",
        "term",
        "category",
        "term_limit_status",
        "occurrence_display",
        "record_date",
        "record_time",
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

    def get_form(self, request, obj=None, **kwargs):
        user = request.user

        class RequestAttendanceRecordForm(AttendanceRecordForm):
            def __init__(self, *args, **kw):
                super().__init__(*args, user=user, **kw)

        kwargs["form"] = RequestAttendanceRecordForm
        return super().get_form(request, obj, **kwargs)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "worker":
            kwargs["queryset"] = filter_workers(
                Worker.objects.select_related("building").order_by("name"),
                request.user,
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        if "category" in request.GET:
            initial["category"] = request.GET["category"]
        return initial

    def save_model(self, request, obj, form, change):
        if not filter_workers(
            Worker.objects.filter(pk=obj.worker_id), request.user
        ).exists():
            raise PermissionDenied("You do not have permission to record attendance for this worker.")
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
                    obj.worker, term, obj.category, record_date
                ):
                    _dispatch_limit_message(request, level, text)
        super().save_model(request, obj, form, change)
        if not change:
            for level, text in limit_warnings_for_record(obj):
                _dispatch_limit_message(request, level, text)


@admin.register(Note)
class NoteModelAdmin(DeleteDockAdminMixin, AuditStampAdminMixin, NoteAdmin):
    audit_fields = ("author",)
    form = NoteForm
    fields = ("building", "worker", "content")
    list_display = ("building", "worker", "author", "created_at", "content_preview")
    list_filter = ("building", "created_at")
    search_fields = ("content", "worker__name", "worker__i_number")
    autocomplete_fields = ("worker",)
    readonly_fields = ("created_at",)

    @admin.display(description="Content")
    def content_preview(self, obj):
        return obj.content[:80] + ("…" if len(obj.content) > 80 else "")

    def get_form(self, request, obj=None, **kwargs):
        user = request.user

        class RequestNoteForm(NoteForm):
            def __init__(self, *args, **kw):
                super().__init__(*args, user=user, **kw)

        kwargs["form"] = RequestNoteForm
        return super().get_form(request, obj, **kwargs)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "building":
            from buildings.models import Building

            kwargs["queryset"] = filter_buildings(
                Building.objects.order_by("name"),
                request.user,
            )
        if db_field.name == "worker":
            kwargs["queryset"] = filter_workers(
                Worker.objects.select_related("building").order_by("name"),
                request.user,
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not user_can_access_building(request.user, obj.building):
            raise PermissionDenied("You do not have permission to use this building.")
        super().save_model(request, obj, form, change)


@admin.register(MonthlyScore)
class MonthlyScoreAdmin(DeleteDockAdminMixin, AuditStampAdminMixin, WorkerRelatedAdmin):
    audit_fields = ("supervisor",)
    list_display = ("worker", "year", "month", "score", "supervisor")
    list_filter = ("year", "month", "worker__building")
    search_fields = ("worker__name", "worker__i_number")
    autocomplete_fields = ("worker",)
