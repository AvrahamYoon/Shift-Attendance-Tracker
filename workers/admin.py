from django.contrib import admin

from config.admin_mixins import (
    AuditStampAdminMixin,
    InlineAuditStampMixin,
    NoteAdmin,
    WorkerAdmin,
    WorkerRelatedAdmin,
)
from workers.models import AttendanceRecord, MonthlyScore, Note, Worker

INLINE_AUDIT_FIELDS = {
    AttendanceRecord: "recorded_by",
    Note: "author",
    MonthlyScore: "supervisor",
}


class AttendanceRecordInline(InlineAuditStampMixin, admin.TabularInline):
    model = AttendanceRecord
    audit_field = "recorded_by"
    extra = 0
    fields = ("category", "subtype", "record_date", "created_at")
    readonly_fields = ("created_at",)


class NoteInline(InlineAuditStampMixin, admin.TabularInline):
    model = Note
    audit_field = "author"
    extra = 0
    fk_name = "worker"
    fields = ("content", "building", "created_at")
    readonly_fields = ("created_at",)


class MonthlyScoreInline(InlineAuditStampMixin, admin.TabularInline):
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
        "position_number",
        "is_lead",
        "shift",
        "term_status",
        "status",
        "supervisor",
    )
    list_filter = ("building", "status", "term_status", "is_lead")
    search_fields = ("name", "i_number", "phone")
    inlines = [AttendanceRecordInline, NoteInline, MonthlyScoreInline]

    def save_model(self, request, obj, form, change):
        if not change and request.user.role == "supervisor":
            obj.supervisor = request.user
            obj.building = request.user.building
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        self._stamp_inline_audit_fields(request, formset)
        super().save_formset(request, form, formset, change)

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

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if request.user.role == "supervisor":
            readonly.extend(["building", "supervisor"])
        return readonly


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(AuditStampAdminMixin, WorkerRelatedAdmin):
    audit_fields = ("recorded_by",)
    list_display = (
        "worker",
        "category",
        "subtype",
        "record_date",
        "recorded_by",
        "created_at",
    )
    list_filter = ("category", "subtype", "record_date", "worker__building")
    search_fields = ("worker__name", "worker__i_number")
    date_hierarchy = "record_date"
    autocomplete_fields = ("worker",)
    readonly_fields = ("created_at",)


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
