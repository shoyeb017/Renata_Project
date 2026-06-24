"""
config_app.loader
==================
Central access point for reading dynamic configuration. All other modules
(analytics engine, streak detection, insights, serializers) MUST go through
these functions rather than referencing activity names or thresholds
directly. This is what enforces the "no hard coding" requirement at the
architectural level: there is exactly one place in the codebase that knows
how to turn a raw REASON string into productivity/category/color, and
exactly one place that knows how to turn a setting name into a typed value.
"""
from functools import lru_cache
from .models import ActivityConfiguration, SystemConfiguration

DEFAULT_CATEGORY = "Uncategorized"
DEFAULT_COLOR = "#6E7681"


def get_or_register_activity(activity_name: str) -> ActivityConfiguration:
    """
    Look up the configuration for an activity name. If it doesn't exist yet
    (a brand-new category appearing in fresh data), auto-register it with
    safe, non-productive defaults instead of failing or silently dropping
    the record. This guarantees the system keeps working when new activity
    categories appear, per the project's resilience requirement.
    """
    activity_name = (activity_name or "Unspecified").strip() or "Unspecified"
    config, created = ActivityConfiguration.objects.get_or_create(
        activity_name__iexact=activity_name,
        defaults={
            "activity_name": activity_name,
            "productive_status": False,
            "category": DEFAULT_CATEGORY,
            "display_color": DEFAULT_COLOR,
            "is_auto_registered": True,
        },
    )
    return config


def all_activity_configs():
    return list(ActivityConfiguration.objects.all())


def activity_lookup_map() -> dict:
    """Returns {activity_name_lower: ActivityConfiguration} for fast joins."""
    return {a.activity_name.lower(): a for a in ActivityConfiguration.objects.all()}


@lru_cache(maxsize=None)
def _get_setting_raw(name: str, default: str):
    try:
        return SystemConfiguration.objects.get(configuration_name=name).configuration_value
    except SystemConfiguration.DoesNotExist:
        return default


def clear_settings_cache():
    _get_setting_raw.cache_clear()


def get_setting_float(name: str, default: float) -> float:
    raw = _get_setting_raw(name, str(default))
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def get_setting_int(name: str, default: int) -> int:
    return int(get_setting_float(name, float(default)))
