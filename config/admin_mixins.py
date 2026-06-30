from django.contrib import admin

from config.permissions import (
    filter_budgets,
    filter_buildings,
    filter_by_worker_relation,
    filter_notes,
    filter_workers,
)


class RoleFilteredAdminMixin:
    """Apply role-based queryset filtering in Django Admin."""

    permission_filter = None

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if self.permission_filter:
            return self.permission_filter(qs, request.user)
        return qs


class WorkerRelatedAdmin(RoleFilteredAdminMixin, admin.ModelAdmin):
    permission_filter = filter_by_worker_relation


class WorkerAdmin(RoleFilteredAdminMixin, admin.ModelAdmin):
    permission_filter = filter_workers


class BuildingAdmin(RoleFilteredAdminMixin, admin.ModelAdmin):
    permission_filter = filter_buildings


class NoteAdmin(RoleFilteredAdminMixin, admin.ModelAdmin):
    permission_filter = filter_notes


class BudgetAdmin(RoleFilteredAdminMixin, admin.ModelAdmin):
    permission_filter = filter_budgets
