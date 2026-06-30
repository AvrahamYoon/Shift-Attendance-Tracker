from django.contrib import admin

from config.admin_mixins import NoteAdmin, WorkerAdmin, WorkerRelatedAdmin
from workers.models import AttendanceRecord, MonthlyScore, Note, Worker


class AttendanceRecordInline(admin.TabularInline):
    model = AttendanceRecord
    extra = 0
    fields = ("category", "subtype", "record_date", "recorded_by", "created_at")
    readonly_fields = ("created_at",)


class NoteInline(admin.TabularInline):
    model = Note
    extra = 0
    fk_name = "worker"
    fields = ("content", "building", "author", "created_at")
    readonly_fields = ("created_at",)


class MonthlyScoreInline(admin.TabularInline):
    model = MonthlyScore
    extra = 0
    fields = ("year", "month", "score", "supervisor")


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

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if request.user.role == "supervisor":
            readonly.extend(["building", "supervisor"])
        return readonly


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(WorkerRelatedAdmin):
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

    def save_model(self, request, obj, form, change):
        if not change:
            obj.recorded_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Note)
class NoteModelAdmin(NoteAdmin):
    list_display = ("building", "worker", "author", "created_at", "content_preview")
    list_filter = ("building", "created_at")
    search_fields = ("content", "worker__name", "worker__i_number")
    autocomplete_fields = ("worker",)

    @admin.display(description="Content")
    def content_preview(self, obj):
        return obj.content[:80] + ("…" if len(obj.content) > 80 else "")

    def save_model(self, request, obj, form, change):
        if not change:
            obj.author = request.user
        if request.user.role == "supervisor" and not obj.building_id:
            obj.building = request.user.building
        super().save_model(request, obj, form, change)


@admin.register(MonthlyScore)
class MonthlyScoreAdmin(WorkerRelatedAdmin):
    list_display = ("worker", "year", "month", "score", "supervisor")
    list_filter = ("year", "month", "worker__building")
    search_fields = ("worker__name", "worker__i_number")
    autocomplete_fields = ("worker",)

    def save_model(self, request, obj, form, change):
        if not change and request.user.role == "supervisor":
            obj.supervisor = request.user
        super().save_model(request, obj, form, change)
