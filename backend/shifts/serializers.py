from rest_framework import serializers
from .models import ShiftRecord, DataQualityReport
from config_app.models import ActivityConfiguration


class ActivityConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityConfiguration
        fields = [
            "id", "activity_name", "productive_status", "category",
            "display_color", "is_auto_registered",
        ]


class ShiftRecordSerializer(serializers.ModelSerializer):
    activity_name = serializers.CharField(source="activity_config.activity_name", read_only=True)
    category = serializers.CharField(source="activity_config.category", read_only=True)
    color = serializers.CharField(source="activity_config.display_color", read_only=True)
    productive = serializers.BooleanField(source="activity_config.productive_status", read_only=True)

    class Meta:
        model = ShiftRecord
        fields = [
            "id", "date", "start_time", "end_time", "duration_hours",
            "activity_reason", "activity_name", "category", "color", "productive",
            "duration_was_recalculated",
        ]


class DataQualityReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataQualityReport
        fields = [
            "id", "run_at", "total_records", "invalid_records",
            "duplicates_removed", "missing_values_handled",
            "duration_mismatches_fixed", "final_clean_records",
        ]
