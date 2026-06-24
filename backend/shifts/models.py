from django.db import models
from config_app.models import ActivityConfiguration


class Dataset(models.Model):
    """
    Represents one ingested CSV - either the bundled default dataset or a
    file a user uploaded through the dashboard. Exactly one Dataset is
    "active" at a time; the API always serves ShiftRecords belonging to
    the active dataset. This is what makes the dataset swappable at
    runtime through the UI rather than only via the DATASET_PATH env var.
    """

    name = models.CharField(max_length=255)
    source = models.CharField(
        max_length=20,
        choices=[("default", "Default bundled dataset"), ("upload", "User upload")],
        default="upload",
    )
    is_active = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    row_count = models.IntegerField(default=0)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.name} ({'active' if self.is_active else 'inactive'})"


class ShiftRecord(models.Model):
    """
    A single cleaned shift/activity record. `activity_reason` is stored as
    free text (whatever the source data says) AND linked to an
    ActivityConfiguration via foreign key, so:
      - the raw value is preserved for audit/debug purposes
      - all productivity/category/color logic flows through the FK,
        never through string comparisons against known names

    Each record belongs to a `dataset`, so uploading a new file doesn't
    delete history - it just changes which dataset is `is_active` and
    therefore visible on the dashboard.

    `source_row_hash` is used to detect and prevent duplicate ingestion of
    the exact same record (same date/start/end/reason) within one dataset.
    """

    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name="shift_records")
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
    source_row_hash = models.CharField(max_length=64, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date", "start_time"]
        indexes = [
            models.Index(fields=["date", "start_time"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["dataset", "source_row_hash"], name="unique_row_per_dataset"),
        ]

    def __str__(self):
        return f"{self.date} {self.activity_reason} ({self.duration_hours}h)"


class DataQualityReport(models.Model):
    """
    Stores the outcome of an ingestion run for a given dataset so the
    dashboard (and developers) can see exactly what the cleaning pipeline
    did, rather than that information being lost after the script finishes.

    Also carries the additional anomaly counters (zero-hour records,
    negative-hour records pre-correction, statistical outliers, duplicate
    count) used by the Data Quality Report panel.
    """

    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name="quality_reports")
    run_at = models.DateTimeField(auto_now_add=True)
    total_records = models.IntegerField(default=0)
    invalid_records = models.IntegerField(default=0)
    duplicates_removed = models.IntegerField(default=0)
    missing_values_handled = models.IntegerField(default=0)
    duration_mismatches_fixed = models.IntegerField(default=0)
    final_clean_records = models.IntegerField(default=0)
    zero_hour_count = models.IntegerField(default=0)
    negative_hour_count = models.IntegerField(default=0)
    outlier_hour_count = models.IntegerField(default=0)
    details_json = models.TextField(blank=True, default="[]")

    class Meta:
        ordering = ["-run_at"]

    def __str__(self):
        return f"Report {self.run_at:%Y-%m-%d %H:%M} - {self.final_clean_records} clean records"
