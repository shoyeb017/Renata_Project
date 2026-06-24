from rest_framework.decorators import api_view
from rest_framework.response import Response

from config_app.loader import get_setting_float, get_setting_int, all_activity_configs
from config_app.models import ActivityConfiguration
from .filters import apply_filters
from .models import ShiftRecord
from .analytics import (
    compute_dashboard_summary,
    compute_shift_analysis_chart_data,
    compute_activity_distribution,
    compute_breakdown_trend,
    compute_failure_heatmap,
    compute_breakdown_streaks,
)
from .insights import generate_insights
from .serializers import ActivityConfigurationSerializer


def _base_queryset(request):
    qs = ShiftRecord.objects.select_related("activity_config").all()
    return apply_filters(request, qs)


@api_view(["GET"])
def dashboard_summary(request):
    qs = _base_queryset(request)
    return Response(compute_dashboard_summary(qs))


@api_view(["GET"])
def shift_analysis(request):
    qs = _base_queryset(request)
    return Response({"blocks": compute_shift_analysis_chart_data(qs)})


@api_view(["GET"])
def activity_distribution(request):
    qs = _base_queryset(request)
    return Response({"distribution": compute_activity_distribution(qs)})


@api_view(["GET"])
def breakdown_trend(request):
    qs = _base_queryset(request)
    return Response({"trend": compute_breakdown_trend(qs)})


@api_view(["GET"])
def failure_heatmap(request):
    qs = _base_queryset(request)
    return Response({"heatmap": compute_failure_heatmap(qs)})


@api_view(["GET"])
def breakdown_streaks(request):
    qs = _base_queryset(request)
    min_events = get_setting_int("breakdown_streak_minimum_events", 3)
    min_hours = get_setting_float("breakdown_streak_minimum_hours", 5)
    max_gap = get_setting_float("breakdown_streak_max_gap_hours", 4)
    streaks = compute_breakdown_streaks(qs, min_events, min_hours, max_gap)
    return Response({
        "streaks": streaks,
        "config": {
            "minimum_events": min_events,
            "minimum_hours": min_hours,
            "max_gap_hours": max_gap,
        },
    })


@api_view(["GET"])
def insights(request):
    qs = _base_queryset(request)
    return Response({"insights": generate_insights(qs)})


@api_view(["GET"])
def filter_options(request):
    """
    Returns the dynamic set of filter choices available right now, derived
    from the database rather than a fixed list - so new activities/
    categories appear here automatically.
    """
    reasons = list(
        ShiftRecord.objects.values_list("activity_reason", flat=True).distinct().order_by("activity_reason")
    )
    categories = list(
        ActivityConfiguration.objects.values_list("category", flat=True).distinct().order_by("category")
    )
    durations = ShiftRecord.objects.values_list("duration_hours", flat=True)
    duration_bounds = {
        "min": round(min(durations), 2) if durations else 0,
        "max": round(max(durations), 2) if durations else 0,
    }
    dates = ShiftRecord.objects.values_list("date", flat=True)
    date_bounds = {
        "min": str(min(dates)) if dates else None,
        "max": str(max(dates)) if dates else None,
    }
    activity_configs = ActivityConfigurationSerializer(all_activity_configs(), many=True).data

    return Response({
        "reasons": reasons,
        "categories": categories,
        "duration_bounds": duration_bounds,
        "date_bounds": date_bounds,
        "activity_configs": activity_configs,
    })
