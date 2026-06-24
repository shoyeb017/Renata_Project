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


def compute_failure_heatmap(queryset) -> list:
    """
    Returns failure hours bucketed by (day_of_week, hour_of_day_bucket).
    Hour buckets are 3-hour windows (0-3, 3-6, ... 21-24) covering a full
    day, computed dynamically rather than assuming any specific shift
    pattern.
    """
    df = _records_to_dataframe(queryset)
    if df.empty:
        return []
    failure_df = df[df["category"].str.lower() == "failure"].copy()
    if failure_df.empty:
        return []

    failure_df["day_of_week"] = failure_df["start_time"].apply(lambda d: d.strftime("%A"))
    failure_df["hour_bucket"] = failure_df["start_time"].apply(lambda d: (d.hour // 3) * 3)

    grouped = failure_df.groupby(["day_of_week", "hour_bucket"])["duration_hours"].sum().reset_index()
    return [
        {
            "day_of_week": row["day_of_week"],
            "hour_bucket_start": int(row["hour_bucket"]),
            "hour_bucket_label": f"{int(row['hour_bucket']):02d}:00-{int(row['hour_bucket']) + 3:02d}:00",
            "failure_hours": round(float(row["duration_hours"]), 2),
        }
        for _, row in grouped.iterrows()
    ]


def compute_breakdown_streaks(queryset, min_events: int, min_hours: float, max_gap_hours: float) -> list:
    """
    Detects continuous/repeated Failure-category periods.

    Assumption (documented per spec requirement "Document assumptions"):
    Records are sorted chronologically by (date, start_time). A "streak"
    is a maximal run of Failure-category events where the gap between one
    event's end and the next event's start is <= max_gap_hours. A streak
    qualifies for reporting only if it has >= min_events events AND its
    total cumulative duration is >= min_hours. Non-failure events do not
    break a streak by themselves being absent - they simply aren't part of
    it; however a Failure event separated from the previous Failure event
    by MORE than max_gap_hours (regardless of what's in between) starts a
    new streak. This treats "continuous or repeated failure periods" as
    failures that recur within a bounded time window of each other, which
    is the practical signal a plant manager cares about (e.g. flapping
    equipment), not strictly back-to-back rows in the dataset.
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

    def flush_streak():
        if not current_events:
            return
        if len(current_events) >= min_events:
            total_hours = sum(e["duration_hours"] for e in current_events)
            if total_hours >= min_hours:
                streaks.append({
                    "start_date": str(current_events[0]["date"]),
                    "start_time": current_events[0]["start_time"].strftime("%Y-%m-%d %H:%M"),
                    "end_date": str(current_events[-1]["date"]),
                    "end_time": current_events[-1]["end_time"].strftime("%Y-%m-%d %H:%M"),
                    "event_count": len(current_events),
                    "total_duration_hours": round(total_hours, 2),
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
    return streaks
