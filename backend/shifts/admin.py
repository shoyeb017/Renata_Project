from django.contrib import admin
from .models import ShiftRecord, DataQualityReport


@admin.register(ShiftRecord)
class ShiftRecordAdmin(admin.ModelAdmin):
    list_display = ("date", "activity_reason", "activity_config", "start_time", "end_time", "duration_hours")
    list_filter = ("activity_config__category", "activity_reason")
    search_fields = ("activity_reason",)
    date_hierarchy = "date"


@admin.register(DataQualityReport)
class DataQualityReportAdmin(admin.ModelAdmin):
    list_display = ("run_at", "total_records", "invalid_records", "duplicates_removed", "final_clean_records")
