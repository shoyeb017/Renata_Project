from django.db import models


class ActivityConfiguration(models.Model):
    """
    Defines how a given activity REASON should be treated by the analytics
    engine. This table is the single source of truth for:
      - whether time spent on an activity counts as productive
      - which category it rolls up into (Failure, Productive, Idle, etc.)
      - what color represents it in the UI

    New activity names that appear in ingested data but are NOT yet present
    here are auto-registered (see shifts/ingestion.py) with a safe default
    (productive=False, category="Uncategorized") rather than being dropped
    or crashing the pipeline. This is what allows the system to tolerate
    new/renamed activity categories without code changes.
    """

    activity_name = models.CharField(max_length=100, unique=True)
    productive_status = models.BooleanField(default=False)
    category = models.CharField(max_length=100, default="Uncategorized")
    display_color = models.CharField(max_length=20, default="#6E7681")
    is_auto_registered = models.BooleanField(
        default=False,
        help_text="True if this row was created automatically because the "
                   "activity appeared in data but had no existing configuration.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["activity_name"]

    def __str__(self):
        return f"{self.activity_name} ({self.category})"


class SystemConfiguration(models.Model):
    """
    Generic key/value configuration store for system-wide thresholds and
    rules (breakdown streak thresholds, efficiency thresholds, etc).
    Values are stored as text and parsed by the consuming code into the
    expected type (int/float/bool), keeping this table generic and
    reusable for any future setting without a schema change.
    """

    configuration_name = models.CharField(max_length=150, unique=True)
    configuration_value = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["configuration_name"]

    def __str__(self):
        return f"{self.configuration_name} = {self.configuration_value}"
