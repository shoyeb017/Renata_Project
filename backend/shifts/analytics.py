"""
shifts.analytics
=================
Reusable analytics functions over ShiftRecord queryset data. Every function
here takes a queryset/dataframe and config lookups as input - none of them
reference a specific activity name. This module is what Phase 6 of the
spec calls the "Analytics Engine".
"""
from collections import defaultdict
from datetime import timedelta

import pandas as pd

from config_app.loader import activity_lookup_map
from .models import ShiftRecord


def _records_to_dataframe(queryset) -> pd.DataFrame:
    rows = list(
        queryset.values(
            "id", "date", "start_time", "end_time", "duration_hours",
            "activity_reason", "activity_config__activity_name",
            "activity_config__productive_status", "activity_config__category",
            "activity_config__display_color",
        )
    )
    if not rows:
        return pd.DataFrame(columns=[
            "id", "date", "start_time", "end_time", "duration_hours",
            "activity_reason", "activity_name", "productive", "category", "color",
        ])
    df = pd.DataFrame(rows)
    df = df.rename(columns={
        "activity_config__activity_name": "activity_name",
        "activity_config__productive_status": "productive",
        "activity_config__category": "category",
        "activity_config__display_color": "color",
    })
    return df


def compute_dashboard_summary(queryset) -> dict:
    df = _records_to_dataframe(queryset)
    if df.empty:
        return {
            "total_hours": 0.0, "productive_hours": 0.0, "downtime_hours": 0.0,
            "efficiency_score": 0.0, "record_count": 0, "date_range": None,
        }

    total_hours = float(df["duration_hours"].sum())
    productive_hours = float(df.loc[df["productive"] == True, "duration_hours"].sum())
    downtime_hours = float(total_hours - productive_hours)
    efficiency = round((productive_hours / total_hours) * 100, 2) if total_hours > 0 else 0.0

    return {
        "total_hours": round(total_hours, 2),
        "productive_hours": round(productive_hours, 2),
        "downtime_hours": round(downtime_hours, 2),
        "efficiency_score": efficiency,
        "record_count": int(len(df)),
        "date_range": {
            "start": str(df["date"].min()),
            "end": str(df["date"].max()),
        },
    }


def compute_shift_analysis_chart_data(queryset) -> list:
    """
    Returns chart-ready blocks for the timeline/Gantt visualization.
    Each block carries enough info for the frontend to position a
    rectangle on a (date x hour-of-day) grid without any further lookups.
    Hour-of-day values can exceed 24 for shifts that cross midnight, so the
    frontend's 0-36 axis can represent them without clipping.
    """
    df = _records_to_dataframe(queryset)
    blocks = []
    for _, row in df.iterrows():
        start_dt = row["start_time"]
        end_dt = row["end_time"]
        day_start = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        start_hour = (start_dt - day_start).total_seconds() / 3600
        end_hour = (end_dt - day_start).total_seconds() / 3600
        blocks.append({
            "id": int(row["id"]),
            "date": str(row["date"]),
            "activity_name": row["activity_name"],
            "category": row["category"],
            "color": row["color"],
            "productive": bool(row["productive"]),
            "start_label": start_dt.strftime("%H:%M"),
            "end_label": end_dt.strftime("%H:%M"),
            "start_hour": round(start_hour, 3),
            "end_hour": round(end_hour, 3),
            "duration_hours": round(float(row["duration_hours"]), 2),
        })
    return blocks


def compute_activity_distribution(queryset) -> list:
    df = _records_to_dataframe(queryset)
    if df.empty:
        return []
    total = df["duration_hours"].sum()
    grouped = (
        df.groupby(["activity_name", "category", "color"])["duration_hours"]
        .sum()
        .reset_index()
        .sort_values("duration_hours", ascending=False)
    )
    result = []
    for _, row in grouped.iterrows():
        pct = round((row["duration_hours"] / total) * 100, 2) if total > 0 else 0.0
        result.append({
            "activity_name": row["activity_name"],
            "category": row["category"],
            "color": row["color"],
            "hours": round(float(row["duration_hours"]), 2),
            "percentage": pct,
        })
    return result


def compute_breakdown_trend(queryset) -> list:
    """Failure-category hours per day, for the Breakdown Trend Chart."""
    df = _records_to_dataframe(queryset)
    if df.empty:
        return []
    failure_df = df[df["category"].str.lower() == "failure"]
    by_day = failure_df.groupby("date")["duration_hours"].sum().reset_index()
    by_day = by_day.sort_values("date")
    return [
        {"date": str(row["date"]), "failure_hours": round(float(row["duration_hours"]), 2)}
        for _, row in by_day.iterrows()
    ]


def compute_breakdown_streaks(queryset, min_events: int, min_hours: float, max_gap_hours: float,
                               severity_thresholds: dict) -> list:
    """
    Detects continuous/repeated Failure-category periods across the WHOLE
    dataset passed in (callers are expected to pass an unfiltered,
    dataset-scoped queryset - this view is explicitly NOT subject to the
    dashboard's interactive filters, since a manager needs to see the
    complete breakdown history regardless of what they're currently
    looking at elsewhere on the page).

    Assumption (documented per spec requirement "Document assumptions"):
    Records are sorted chronologically by (date, start_time). A "streak"
    is a maximal run of Failure-category events where the gap between one
    event's end and the next event's start is <= max_gap_hours. A streak
    qualifies for reporting only if it has >= min_events events AND its
    total cumulative duration is >= min_hours. A Failure event separated
    from the previous Failure event by MORE than max_gap_hours starts a
    new streak. This treats "continuous or repeated failure periods" as
    failures that recur within a bounded time window of each other, which
    is the practical signal a plant manager cares about (e.g. flapping
    equipment), not strictly back-to-back rows in the dataset.

    Each returned streak also reports a `severity` derived from its
    average hours of impact per calendar day spanned, classified against
    configurable thresholds (see SystemConfiguration: severity_*_avg_hours)
    rather than a hardcoded number.
    """
    df = _records_to_dataframe(queryset)
    if df.empty:
        return []

    failure_df = df[df["category"].str.lower() == "failure"].copy()
    if failure_df.empty:
        return []

    failure_df = failure_df.sort_values(["date", "start_time"]).reset_index(drop=True)

    streaks = []
    current_events = []

    def classify_severity(avg_hours_per_day: float) -> str:
        if avg_hours_per_day >= severity_thresholds["critical"]:
            return "Critical"
        if avg_hours_per_day >= severity_thresholds["high"]:
            return "High"
        if avg_hours_per_day >= severity_thresholds["medium"]:
            return "Medium"
        return "Low"

    def flush_streak():
        if not current_events:
            return
        if len(current_events) >= min_events:
            total_hours = sum(e["duration_hours"] for e in current_events)
            if total_hours >= min_hours:
                start_date = current_events[0]["date"]
                end_date = current_events[-1]["date"]
                duration_days = max((end_date - start_date).days + 1, 1)
                avg_per_day = round(total_hours / duration_days, 2)
                streaks.append({
                    "start_date": str(start_date),
                    "end_date": str(end_date),
                    "start_time": current_events[0]["start_time"].strftime("%Y-%m-%d %H:%M"),
                    "end_time": current_events[-1]["end_time"].strftime("%Y-%m-%d %H:%M"),
                    "duration_days": duration_days,
                    "event_count": len(current_events),
                    "total_hours": round(total_hours, 2),
                    "avg_hours_per_day": avg_per_day,
                    "severity": classify_severity(avg_per_day),
                    "activities": sorted({e["activity_name"] for e in current_events}),
                })

    previous_end = None
    for _, row in failure_df.iterrows():
        if previous_end is not None:
            gap_hours = (row["start_time"] - previous_end).total_seconds() / 3600
            if gap_hours > max_gap_hours:
                flush_streak()
                current_events = []
        current_events.append(row)
        previous_end = row["end_time"]

    flush_streak()
    streaks.sort(key=lambda s: s["total_hours"], reverse=True)
    return streaks


def compute_breakdown_streak_timeline(queryset) -> list:
    """
    Returns Failure-category hours per day across the WHOLE dataset
    (no filters), for the streak visualization chart - lets the frontend
    plot exactly where in the timeline failures (and streaks of them)
    occurred, independent of whatever the interactive filters are set to
    elsewhere on the dashboard.
    """
    df = _records_to_dataframe(queryset)
    if df.empty:
        return []
    failure_df = df[df["category"].str.lower() == "failure"]
    if failure_df.empty:
        return []
    by_day = failure_df.groupby("date")["duration_hours"].sum().reset_index().sort_values("date")
    return [
        {"date": str(row["date"]), "failure_hours": round(float(row["duration_hours"]), 2)}
        for _, row in by_day.iterrows()
    ]


def compute_data_quality_report(queryset, quality_report) -> dict:
    """
    Builds the Data Quality Report panel payload: validity percentage,
    record counts, aggregate hours/duration stats, category count, and
    the anomaly breakdown captured during cleaning (zero/negative/outlier
    hours, duplicates). `quality_report` is the DataQualityReport row
    produced when this dataset was ingested - this function does not
    recompute cleaning-time facts, only summarizes them alongside live
    stats over the currently-stored (already cleaned) records.

    This is intentionally NOT subject to dashboard filters: it reports on
    the dataset as ingested, which is a fixed historical fact, not a
    live filtered view.
    """
    df = _records_to_dataframe(queryset)

    total_records = quality_report.total_records if quality_report else len(df)
    final_clean_records = quality_report.final_clean_records if quality_report else len(df)
    invalid_records = quality_report.invalid_records if quality_report else 0
    valid_records = final_clean_records - invalid_records if quality_report else len(df)
    valid_records = max(valid_records, 0)

    validity_pct = round((valid_records / total_records) * 100, 2) if total_records > 0 else 0.0

    total_hours = float(df["duration_hours"].sum()) if not df.empty else 0.0
    avg_duration = float(df["duration_hours"].mean()) if not df.empty else 0.0
    category_count = int(df["category"].nunique()) if not df.empty else 0

    return {
        "data_validity_pct": validity_pct,
        "total_records": total_records,
        "valid_records": valid_records,
        "invalid_records": invalid_records,
        "total_hours": round(total_hours, 2),
        "avg_shift_duration_hours": round(avg_duration, 2),
        "category_count": category_count,
        "anomalies": {
            "zero_hours": quality_report.zero_hour_count if quality_report else 0,
            "negative_hours": quality_report.negative_hour_count if quality_report else 0,
            "outlier_hours_95th_percentile": quality_report.outlier_hour_count if quality_report else 0,
            "duplicate_records": quality_report.duplicates_removed if quality_report else 0,
        },
    }
