from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from config_app.loader import get_setting_float, get_setting_int, all_activity_configs
from config_app.models import ActivityConfiguration
from .filters import apply_filters
from .models import ShiftRecord, Dataset, DataQualityReport
from .ingestion import ingest_csv_file
from .analytics import (
    compute_dashboard_summary,
    compute_shift_analysis_chart_data,
    compute_activity_distribution,
    compute_breakdown_trend,
    compute_breakdown_streaks,
    compute_breakdown_streak_timeline,
    compute_data_quality_report,
)
from .insights import generate_insights
from .serializers import ActivityConfigurationSerializer, DatasetSerializer


def _active_dataset():
    return Dataset.objects.filter(is_active=True).first()


def _active_dataset_queryset():
    """
    Unfiltered queryset scoped ONLY to the active dataset. Used by panels
    that must reflect the whole dataset regardless of the dashboard's
    interactive filters (Breakdown Streaks, Data Quality Report).
    """
    dataset = _active_dataset()
    if dataset is None:
        return ShiftRecord.objects.none()
    return ShiftRecord.objects.select_related("activity_config").filter(dataset=dataset)


def _base_queryset(request):
    """
    Filtered queryset scoped to the active dataset. Used by the panels
    that DO respect dashboard filters (KPIs, Shift Analysis, Activity
    Distribution, Breakdown Trend, Insights).
    """
    qs = _active_dataset_queryset()
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
def breakdown_streaks(request):
    """
    Breakdown streak detection over the ENTIRE active dataset. Deliberately
    ignores all query-string filters (date_from, reason, category, etc.) -
    breakdown risk is a standing fact about the dataset, not something
    that should change because of an unrelated filter selection elsewhere
    on the dashboard.
    """
    qs = _active_dataset_queryset()
    min_events = get_setting_int("breakdown_streak_minimum_events", 2)
    min_hours = get_setting_float("breakdown_streak_minimum_hours", 4)
    max_gap = get_setting_float("breakdown_streak_max_gap_hours", 6)
    severity_thresholds = {
        "critical": get_setting_float("streak_severity_critical_avg_hours", 8),
        "high": get_setting_float("streak_severity_high_avg_hours", 5),
        "medium": get_setting_float("streak_severity_medium_avg_hours", 2),
    }
    streaks = compute_breakdown_streaks(qs, min_events, min_hours, max_gap, severity_thresholds)
    timeline = compute_breakdown_streak_timeline(qs)
    return Response({
        "streaks": streaks,
        "timeline": timeline,
        "config": {
            "minimum_events": min_events,
            "minimum_hours": min_hours,
            "max_gap_hours": max_gap,
        },
    })


@api_view(["GET"])
def data_quality_report(request):
    """
    Data Quality Report for the ENTIRE active dataset, as ingested.
    Deliberately ignores dashboard filters - this reports on a fixed
    historical fact (how clean was the data when it was loaded), not a
    live filtered view.
    """
    qs = _active_dataset_queryset()
    dataset = _active_dataset()
    quality_report = (
        DataQualityReport.objects.filter(dataset=dataset).order_by("-run_at").first()
        if dataset else None
    )
    return Response(compute_data_quality_report(qs, quality_report))


@api_view(["GET"])
def insights(request):
    qs = _base_queryset(request)
    return Response({"insights": generate_insights(qs)})


@api_view(["GET"])
def filter_options(request):
    """
    Returns the dynamic set of filter choices available right now for the
    ACTIVE dataset, derived from the database rather than a fixed list -
    so new activities/categories appear here automatically, and switching
    datasets changes what's offered.
    """
    qs = _active_dataset_queryset()
    reasons = list(qs.values_list("activity_reason", flat=True).distinct().order_by("activity_reason"))
    categories = list(
        ActivityConfiguration.objects.filter(shift_records__in=qs)
        .values_list("category", flat=True).distinct().order_by("category")
    )
    durations = list(qs.values_list("duration_hours", flat=True))
    duration_bounds = {
        "min": round(min(durations), 2) if durations else 0,
        "max": round(max(durations), 2) if durations else 0,
    }
    dates = list(qs.values_list("date", flat=True))
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


@api_view(["GET"])
def list_datasets(request):
    """Lists every dataset ever ingested (bundled default + uploads), most recent first."""
    datasets = Dataset.objects.all()
    return Response({"datasets": DatasetSerializer(datasets, many=True).data})


@api_view(["POST"])
@parser_classes([MultiPartParser])
def upload_dataset(request):
    """
    Accepts a CSV upload (multipart field name: 'file'), runs it through
    the exact same cleaning + ingestion pipeline as the bundled dataset,
    stores it as a new Dataset, and makes it active. The previously
    active dataset is kept (not deleted) so a user can switch back via
    /api/datasets/<id>/activate.
    """
    uploaded_file = request.FILES.get("file")
    if uploaded_file is None:
        return Response({"error": "No file provided. Send multipart/form-data with field name 'file'."}, status=400)

    if not uploaded_file.name.lower().endswith(".csv"):
        return Response({"error": "Only .csv files are supported."}, status=400)

    try:
        result = ingest_csv_file(uploaded_file, dataset_name=uploaded_file.name, source="upload", activate=True)
    except Exception as exc:
        return Response({"error": f"Failed to process file: {exc}"}, status=400)

    return Response(result, status=201)


@api_view(["POST"])
def activate_dataset(request, dataset_id):
    """Switches the active dataset to a previously ingested one (e.g. revert to the default)."""
    try:
        dataset = Dataset.objects.get(id=dataset_id)
    except Dataset.DoesNotExist:
        return Response({"error": "Dataset not found."}, status=404)

    Dataset.objects.filter(is_active=True).update(is_active=False)
    dataset.is_active = True
    dataset.save(update_fields=["is_active"])
    return Response(DatasetSerializer(dataset).data)
