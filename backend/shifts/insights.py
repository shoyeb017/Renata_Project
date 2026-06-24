"""
shifts.insights
================
Generates plant-manager-facing insight sentences purely from computed data.
No insight text is fixed/static; every sentence interpolates real numbers,
activity names, dates, or time windows produced by the analytics engine for
the *current* filtered queryset. If the underlying data changes, the wording
and conclusions change with it.
"""
from .analytics import (
    _records_to_dataframe,
    compute_dashboard_summary,
    compute_activity_distribution,
    compute_failure_heatmap,
    compute_breakdown_streaks,
)
from config_app.loader import get_setting_float


def generate_insights(queryset) -> list:
    insights = []
    df = _records_to_dataframe(queryset)
    if df.empty:
        return [{"category": "Data", "text": "No shift records are available for the selected filters."}]

    min_sample_hours = get_setting_float("insight_minimum_sample_hours", 1.0)

    # 1. Efficiency insight
    summary = compute_dashboard_summary(queryset)
    low_threshold = get_setting_float("efficiency_low_threshold_pct", 70.0)
    eff = summary["efficiency_score"]
    if eff < low_threshold:
        insights.append({
            "category": "Efficiency",
            "text": (
                f"Operational efficiency is {eff}%, below the {low_threshold}% target, "
                f"with {summary['downtime_hours']}h of non-productive time out of "
                f"{summary['total_hours']}h total."
            ),
        })
    else:
        insights.append({
            "category": "Efficiency",
            "text": (
                f"Operational efficiency is {eff}%, at or above the {low_threshold}% target, "
                f"driven by {summary['productive_hours']}h of productive time out of "
                f"{summary['total_hours']}h total."
            ),
        })

    # 2. Top downtime driver
    distribution = compute_activity_distribution(queryset)
    failure_items = [d for d in distribution if d["category"].lower() == "failure" and d["hours"] >= min_sample_hours]
    if failure_items:
        top = failure_items[0]
        insights.append({
            "category": "Downtime Driver",
            "text": (
                f"\"{top['activity_name']}\" is the leading failure cause, accounting for "
                f"{top['hours']}h ({top['percentage']}% of all recorded time)."
            ),
        })

    non_failure_non_productive = [
        d for d in distribution
        if d["category"].lower() not in ("failure", "productive") and d["hours"] >= min_sample_hours
    ]
    if non_failure_non_productive:
        top_other = non_failure_non_productive[0]
        insights.append({
            "category": "Secondary Loss",
            "text": (
                f"\"{top_other['activity_name']}\" ({top_other['category']}) consumed "
                f"{top_other['hours']}h ({top_other['percentage']}%), the largest non-failure, "
                f"non-productive contributor."
            ),
        })

    # 3. Failure timing pattern
    heatmap = compute_failure_heatmap(queryset)
    if heatmap:
        peak = max(heatmap, key=lambda h: h["failure_hours"])
        if peak["failure_hours"] >= min_sample_hours:
            insights.append({
                "category": "Failure Timing",
                "text": (
                    f"Failures are most concentrated on {peak['day_of_week']}s between "
                    f"{peak['hour_bucket_label']}, totalling {peak['failure_hours']}h in that window."
                ),
            })

    # 4. Breakdown streaks
    min_events = int(get_setting_float("breakdown_streak_minimum_events", 3))
    min_hours = get_setting_float("breakdown_streak_minimum_hours", 5)
    max_gap = get_setting_float("breakdown_streak_max_gap_hours", 4)
    streaks = compute_breakdown_streaks(queryset, min_events, min_hours, max_gap)
    if streaks:
        longest = max(streaks, key=lambda s: s["total_duration_hours"])
        insights.append({
            "category": "Breakdown Streak",
            "text": (
                f"A breakdown streak was detected from {longest['start_time']} to {longest['end_time']} "
                f"spanning {longest['event_count']} events and {longest['total_duration_hours']}h "
                f"({', '.join(longest['activities'])})."
            ),
        })

    # 5. Recently auto-registered/uncategorized activity flag
    uncategorized = [d for d in distribution if d["category"].lower() == "uncategorized" and d["hours"] >= min_sample_hours]
    if uncategorized:
        item = uncategorized[0]
        insights.append({
            "category": "Configuration",
            "text": (
                f"\"{item['activity_name']}\" appeared in the data without a configured category "
                f"({item['hours']}h recorded). Review and classify it in Activity Configuration."
            ),
        })

    return insights
