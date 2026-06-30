from django.contrib import admin

from buildings.models import Building
from config.admin_mixins import BuildingAdmin


@admin.register(Building)
class BuildingModelAdmin(BuildingAdmin):
    list_display = ("name", "address", "active_headcount_display")
    search_fields = ("name", "address")

    @admin.display(description="Active workers")
    def active_headcount_display(self, obj):
        return obj.active_headcount
