from django.contrib import admin
from .models import ShiftRecord, DataQualityReport, Dataset


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = ("name", "source", "is_active", "row_count", "uploaded_at")
    list_filter = ("source", "is_active")


@admin.register(ShiftRecord)
class ShiftRecordAdmin(admin.ModelAdmin):
    list_display = ("date", "activity_reason", "activity_config", "dataset", "start_time", "end_time", "duration_hours")
    list_filter = ("dataset", "activity_config__category", "activity_reason")
    search_fields = ("activity_reason",)
    date_hierarchy = "date"


@admin.register(DataQualityReport)
class DataQualityReportAdmin(admin.ModelAdmin):
    list_display = ("dataset", "run_at", "total_records", "invalid_records", "duplicates_removed", "final_clean_records")
