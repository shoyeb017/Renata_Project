from django.db import models
from config_app.models import ActivityConfiguration


class ShiftRecord(models.Model):
    """
    A single cleaned shift/activity record. `activity_reason` is stored as
    free text (whatever the source data says) AND linked to an
    ActivityConfiguration via foreign key, so:
      - the raw value is preserved for audit/debug purposes
      - all productivity/category/color logic flows through the FK,
        never through string comparisons against known names

    `source_row_hash` is used to detect and prevent duplicate ingestion of
    the exact same record (same date/start/end/reason) across re-runs of
    the ingestion command.
    """

    date = models.DateField(db_index=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    duration_hours = models.FloatField()
    activity_reason = models.CharField(max_length=150)
    activity_config = models.ForeignKey(
        ActivityConfiguration,
        on_delete=models.PROTECT,
        related_name="shift_records",
    )
    duration_was_recalculated = models.BooleanField(
        default=False,
        help_text="True if the original HOURS value didn't match END-START "
                   "and was recalculated during cleaning.",
    )
    source_row_hash = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date", "start_time"]
        indexes = [
            models.Index(fields=["date", "start_time"]),
        ]

    def __str__(self):
        return f"{self.date} {self.activity_reason} ({self.duration_hours}h)"


class DataQualityReport(models.Model):
    """
    Stores the outcome of the most recent ingestion run so the dashboard
    (and developers) can see exactly what the cleaning pipeline did,
    rather than that information being lost after the script finishes.
    """

    run_at = models.DateTimeField(auto_now_add=True)
    total_records = models.IntegerField(default=0)
    invalid_records = models.IntegerField(default=0)
    duplicates_removed = models.IntegerField(default=0)
    missing_values_handled = models.IntegerField(default=0)
    duration_mismatches_fixed = models.IntegerField(default=0)
    final_clean_records = models.IntegerField(default=0)
    details_json = models.TextField(blank=True, default="[]")

    class Meta:
        ordering = ["-run_at"]

    def __str__(self):
        return f"Report {self.run_at:%Y-%m-%d %H:%M} - {self.final_clean_records} clean records"
