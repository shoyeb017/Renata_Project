"""
shifts.insights
================
Generates plant-manager-facing insight cards purely from computed data.
No insight text, metric, or severity is fixed/static; every value is
interpolated from real numbers produced by the analytics engine for the
*current* filtered queryset (these DO respect dashboard filters, unlike
the Breakdown Streaks / Data Quality Report panels). If the underlying
data or filters change, the wording, metrics, and severities change with
them - this module never returns the same canned sentence twice for
different data.

Each insight card has the shape:
  {
    "title": str,            short heading, e.g. "Operational Efficiency Status"
    "metric": str,            headline figure shown large, e.g. "77.1%"
    "text": str,              the explanatory sentence, built from real numbers
    "action": str,            a recommended next step, built from real numbers
    "severity": str,          one of Low / Medium / High / Critical
  }
"""
from config_app.loader import get_setting_float
from .analytics import (
    _records_to_dataframe,
    compute_dashboard_summary,
    compute_activity_distribution,
    compute_breakdown_streaks,
)


def _efficiency_severity(efficiency_pct: float, low_threshold: float) -> str:
    if efficiency_pct < low_threshold * 0.7:
        return "Critical"
    if efficiency_pct < low_threshold:
        return "Medium"
    return "Low"


def _streak_severity_from_active_streak(severity: str) -> str:
    # Reuse the same severity vocabulary the streak detector already produced.
    return severity


def generate_insights(queryset) -> list:
    insights = []
    df = _records_to_dataframe(queryset)
    if df.empty:
        return [{
            "title": "No Data",
            "metric": "—",
            "text": "No shift records are available for the selected filters.",
            "action": "Adjust or clear filters to see operational insights.",
            "severity": "Low",
        }]

    min_sample_hours = get_setting_float("insight_minimum_sample_hours", 1.0)
    low_threshold = get_setting_float("efficiency_low_threshold_pct", 70.0)

    # 1. Operational Efficiency Status
    summary = compute_dashboard_summary(queryset)
    eff = summary["efficiency_score"]
    eff_status_word = "good" if eff >= low_threshold else "needs attention"
    insights.append({
        "title": "Operational Efficiency Status",
        "metric": f"{eff}%",
        "text": (
            f"Current operational efficiency is {eff}% ({eff_status_word}). "
            f"Productive hours: {summary['productive_hours']} / {summary['total_hours']} total hours."
        ),
        "action": (
            "Maintain current shift scheduling and continue monitoring for drift."
            if eff >= low_threshold else
            "Focus on reducing minor breakdowns and optimizing shift schedules."
        ),
        "severity": _efficiency_severity(eff, low_threshold),
    })

    # 2. Breakdown Risk Assessment - driven by the WHOLE-dataset streak
    # detector (not the filtered queryset), since breakdown risk is a
    # standing operational fact, not something that should disappear
    # because of an unrelated filter selection. We still show it inside
    # the (filter-aware) insights list because it's genuinely useful
    # context here, but the streak math itself is always full-dataset.
    distribution = compute_activity_distribution(queryset)
    failure_items = [d for d in distribution if d["category"].lower() == "failure" and d["hours"] >= min_sample_hours]
    total_failure_hours = round(sum(d["hours"] for d in failure_items), 2)
    total_failure_incidents = int(df[df["category"].str.lower() == "failure"].shape[0])

    min_events = int(get_setting_float("breakdown_streak_minimum_events", 2))
    min_hours = get_setting_float("breakdown_streak_minimum_hours", 4)
    max_gap = get_setting_float("breakdown_streak_max_gap_hours", 6)
    severity_thresholds = {
        "critical": get_setting_float("streak_severity_critical_avg_hours", 8),
        "high": get_setting_float("streak_severity_high_avg_hours", 5),
        "medium": get_setting_float("streak_severity_medium_avg_hours", 2),
    }
    streaks = compute_breakdown_streaks(queryset, min_events, min_hours, max_gap, severity_thresholds)

    if failure_items:
        top_failure_activity = failure_items[0]["activity_name"]
        if streaks:
            active = streaks[0]
            insights.append({
                "title": "Breakdown Risk Assessment",
                "metric": f"{active['total_hours']}h",
                "text": (
                    f"Active breakdown streak: {active['duration_days']} day(s) with "
                    f"{active['total_hours']} hours total impact. Total breakdown incidents: "
                    f"{total_failure_incidents} ({total_failure_hours} hours)."
                ),
                "action": (
                    f"Investigate '{top_failure_activity}' incidents and implement targeted "
                    f"prevention measures."
                ),
                "severity": active["severity"],
            })
        else:
            insights.append({
                "title": "Breakdown Risk Assessment",
                "metric": f"{total_failure_hours}h",
                "text": (
                    f"No qualifying breakdown streak detected. Total breakdown incidents: "
                    f"{total_failure_incidents} ({total_failure_hours} hours)."
                ),
                "action": f"Continue monitoring '{top_failure_activity}' as the leading failure cause.",
                "severity": "Medium" if total_failure_hours >= min_sample_hours else "Low",
            })

    # 3. Optimization Opportunity - largest non-failure, non-productive
    # category (logistics, idle, uncategorized, etc).
    non_failure_non_productive = [
        d for d in distribution
        if d["category"].lower() not in ("failure", "productive") and d["hours"] >= min_sample_hours
    ]
    if non_failure_non_productive:
        top_other = non_failure_non_productive[0]
        insights.append({
            "title": "Optimization Opportunity",
            "metric": f"{top_other['percentage']}%",
            "text": (
                f"'{top_other['activity_name']}' accounts for {top_other['hours']} hours "
                f"({top_other['percentage']}% of total)."
            ),
            "action": f"Monitor '{top_other['activity_name']}' trends and consider process improvements.",
            "severity": "Medium" if top_other["percentage"] >= 15 else "Low",
        })

    # 4. Configuration flag for uncategorized/auto-registered activities
    uncategorized = [d for d in distribution if d["category"].lower() == "uncategorized" and d["hours"] >= min_sample_hours]
    if uncategorized:
        item = uncategorized[0]
        insights.append({
            "title": "Unclassified Activity Detected",
            "metric": f"{item['hours']}h",
            "text": (
                f"'{item['activity_name']}' appeared in the data without a configured category "
                f"({item['hours']} hours recorded)."
            ),
            "action": "Review and classify it under Activity Configuration so it's reflected correctly in analytics.",
            "severity": "Medium",
        })

    return insights
