"""
Tests for the data cleaning pipeline, analytics engine, and API layer.
Run with: python manage.py test
"""
import json
from datetime import date, datetime, timezone as dt_timezone

import pandas as pd
from django.test import TestCase
from rest_framework.test import APIClient

from config_app.models import ActivityConfiguration, SystemConfiguration
from .cleaning import clean_dataframe
from .models import ShiftRecord
from .analytics import (
    compute_dashboard_summary,
    compute_breakdown_streaks,
    compute_activity_distribution,
)
from .insights import generate_insights


# ---------------------------------------------------------------------------
# Data cleaning tests
# ---------------------------------------------------------------------------
class CleaningPipelineTests(TestCase):
    def _df(self, rows):
        return pd.DataFrame(rows, columns=["DAY_DATE", "START", "END", "HOURS", "REASON"])

    def test_missing_start_is_derived_from_end_and_hours(self):
        df = self._df([
            ["10/12/2025", None, "2025-10-12T18:28:00Z", "3.3", "Breakdown"],
        ])
        clean_df, report = clean_dataframe(df)
        self.assertEqual(len(clean_df), 1)
        self.assertEqual(report.missing_values_handled, 1)
        self.assertEqual(clean_df.iloc[0]["duration_hours"], 3.3)

    def test_missing_end_is_derived_from_start_and_hours(self):
        df = self._df([
            ["10/12/2025", "2025-10-12T18:10:00Z", None, "2.7", "Power Failure"],
        ])
        clean_df, report = clean_dataframe(df)
        self.assertEqual(len(clean_df), 1)
        self.assertEqual(report.missing_values_handled, 1)

    def test_row_missing_both_start_and_end_is_dropped(self):
        df = self._df([
            ["10/12/2025", None, None, "2.7", "Power Failure"],
        ])
        clean_df, report = clean_dataframe(df)
        self.assertEqual(len(clean_df), 0)
        self.assertEqual(report.invalid_records, 1)

    def test_duration_mismatch_is_recalculated_from_timestamps(self):
        df = self._df([
            ["10/8/2025", "2025-10-08T17:45:00Z", "2025-10-08T20:27:00Z", "-3", "Other"],
        ])
        clean_df, report = clean_dataframe(df)
        self.assertEqual(len(clean_df), 1)
        self.assertAlmostEqual(clean_df.iloc[0]["duration_hours"], 2.7, places=2)
        self.assertTrue(clean_df.iloc[0]["duration_was_recalculated"])
        self.assertEqual(report.duration_mismatches_fixed, 1)

    def test_malformed_date_is_derived_from_start_timestamp(self):
        df = self._df([
            ["2025-15-55", "2025-10-07T15:15:00Z", "2025-10-07T16:39:00Z", "1.4", "Cleaning"],
        ])
        clean_df, report = clean_dataframe(df)
        self.assertEqual(len(clean_df), 1)
        self.assertEqual(clean_df.iloc[0]["date"], date(2025, 10, 7))

    def test_invalid_timestamp_string_is_treated_as_missing(self):
        df = self._df([
            ["10/1/2025", "invalid-time", "2025-10-01T08:24:00Z", "1.4", "Breakdown"],
        ])
        clean_df, report = clean_dataframe(df)
        self.assertEqual(len(clean_df), 1)
        # Should have derived START from END - HOURS since the literal START was unparseable.
        self.assertEqual(report.missing_values_handled, 1)

    def test_overnight_shift_end_before_start_is_handled(self):
        df = self._df([
            ["10/4/2025", "2025-10-04T22:00:00Z", "2025-10-05T02:00:00Z", "4", "Maintenance"],
        ])
        clean_df, report = clean_dataframe(df)
        self.assertEqual(len(clean_df), 1)
        self.assertEqual(clean_df.iloc[0]["duration_hours"], 4.0)

    def test_implausible_overnight_gap_is_dropped(self):
        # END appears before START by an amount that would imply a >16h
        # overnight shift if naively rolled forward - should be rejected.
        df = self._df([
            ["10/4/2025", "2025-10-04T08:00:00Z", "2025-10-04T01:00:00Z", "1", "Maintenance"],
        ])
        clean_df, report = clean_dataframe(df)
        self.assertEqual(len(clean_df), 0)
        self.assertEqual(report.invalid_records, 1)

    def test_exact_duplicate_rows_are_removed(self):
        row = ["10/20/2025", "2025-10-20T07:30:00Z", "2025-10-20T09:30:00Z", "2", "Cleaning"]
        df = self._df([row, row])
        clean_df, report = clean_dataframe(df)
        self.assertEqual(len(clean_df), 1)
        self.assertEqual(report.duplicates_removed, 1)

    def test_missing_reason_defaults_to_unspecified(self):
        df = self._df([
            ["10/1/2025", "2025-10-01T07:00:00Z", "2025-10-01T08:00:00Z", "1", None],
        ])
        clean_df, report = clean_dataframe(df)
        self.assertEqual(clean_df.iloc[0]["activity_reason"], "Unspecified")
        self.assertEqual(report.missing_values_handled, 1)

    def test_report_totals_are_internally_consistent(self):
        rows = [
            ["10/1/2025", "2025-10-01T07:00:00Z", "2025-10-01T08:00:00Z", "1", "Training"],
            ["10/2/2025", None, None, "1", "Training"],  # dropped: both missing
        ]
        df = self._df(rows)
        clean_df, report = clean_dataframe(df)
        self.assertEqual(report.total_records, 2)
        self.assertEqual(report.final_clean_records, len(clean_df))
        self.assertEqual(report.final_clean_records, report.total_records - report.invalid_records - report.duplicates_removed)


# ---------------------------------------------------------------------------
# Analytics engine tests
# ---------------------------------------------------------------------------
class AnalyticsEngineTests(TestCase):
    def setUp(self):
        self.productive_cfg = ActivityConfiguration.objects.create(
            activity_name="Training", productive_status=True, category="Productive", display_color="#2E8B7E",
        )
        self.failure_cfg = ActivityConfiguration.objects.create(
            activity_name="Breakdown", productive_status=False, category="Failure", display_color="#C44536",
        )
        self._make_record("2025-10-01", "07:00", "09:00", self.productive_cfg, "Training")
        self._make_record("2025-10-01", "09:00", "11:00", self.failure_cfg, "Breakdown")

    def _make_record(self, date_str, start_str, end_str, cfg, reason):
        start = datetime.fromisoformat(f"{date_str}T{start_str}:00+00:00")
        end = datetime.fromisoformat(f"{date_str}T{end_str}:00+00:00")
        return ShiftRecord.objects.create(
            date=date_str,
            start_time=start,
            end_time=end,
            duration_hours=(end - start).total_seconds() / 3600,
            activity_reason=reason,
            activity_config=cfg,
            source_row_hash=f"{date_str}{start_str}{end_str}{reason}",
        )

    def test_dashboard_summary_efficiency_calculation(self):
        qs = ShiftRecord.objects.all()
        summary = compute_dashboard_summary(qs)
        self.assertEqual(summary["total_hours"], 4.0)
        self.assertEqual(summary["productive_hours"], 2.0)
        self.assertEqual(summary["efficiency_score"], 50.0)

    def test_dashboard_summary_with_no_records(self):
        summary = compute_dashboard_summary(ShiftRecord.objects.none())
        self.assertEqual(summary["total_hours"], 0.0)
        self.assertEqual(summary["efficiency_score"], 0.0)

    def test_activity_distribution_percentages_sum_to_100(self):
        qs = ShiftRecord.objects.all()
        dist = compute_activity_distribution(qs)
        total_pct = sum(d["percentage"] for d in dist)
        self.assertAlmostEqual(total_pct, 100.0, places=1)

    def test_breakdown_streak_requires_minimum_events(self):
        # Only one failure event exists in setUp - should not qualify as a streak.
        qs = ShiftRecord.objects.all()
        streaks = compute_breakdown_streaks(qs, min_events=3, min_hours=1, max_gap_hours=4)
        self.assertEqual(streaks, [])

    def test_breakdown_streak_detected_when_thresholds_met(self):
        # Add two more close-together failure events to form a streak of 3.
        self._make_record("2025-10-01", "11:30", "13:00", self.failure_cfg, "Breakdown")
        self._make_record("2025-10-01", "13:30", "15:00", self.failure_cfg, "Breakdown")
        qs = ShiftRecord.objects.all()
        streaks = compute_breakdown_streaks(qs, min_events=3, min_hours=1, max_gap_hours=4)
        self.assertEqual(len(streaks), 1)
        self.assertEqual(streaks[0]["event_count"], 3)

    def test_breakdown_streak_broken_by_large_gap(self):
        self._make_record("2025-10-05", "09:00", "10:00", self.failure_cfg, "Breakdown")
        self._make_record("2025-10-05", "20:00", "21:00", self.failure_cfg, "Breakdown")
        qs = ShiftRecord.objects.all()
        # max_gap_hours=4 means the 09:00-10:00 and 20:00-21:00 events
        # (10h apart) should NOT be grouped into the same streak.
        streaks = compute_breakdown_streaks(qs, min_events=2, min_hours=0.5, max_gap_hours=4)
        for streak in streaks:
            self.assertLess(streak["event_count"], 3)

    def test_insights_are_generated_from_data(self):
        qs = ShiftRecord.objects.all()
        insights = generate_insights(qs)
        self.assertGreaterEqual(len(insights), 1)
        # Every insight must reference at least one number (a digit), proving
        # it's derived from computed data rather than being static text.
        for insight in insights:
            self.assertTrue(any(ch.isdigit() for ch in insight["text"]))


# ---------------------------------------------------------------------------
# Config auto-registration tests
# ---------------------------------------------------------------------------
class ActivityConfigAutoRegistrationTests(TestCase):
    def test_unknown_activity_is_auto_registered_not_dropped(self):
        from config_app.loader import get_or_register_activity
        cfg = get_or_register_activity("Brand New Category")
        self.assertTrue(cfg.is_auto_registered)
        self.assertEqual(cfg.category, "Uncategorized")
        self.assertFalse(cfg.productive_status)

    def test_known_activity_lookup_is_case_insensitive_and_not_duplicated(self):
        from config_app.loader import get_or_register_activity
        ActivityConfiguration.objects.create(
            activity_name="Training", productive_status=True, category="Productive",
        )
        cfg = get_or_register_activity("training")
        self.assertFalse(cfg.is_auto_registered)
        self.assertEqual(ActivityConfiguration.objects.filter(activity_name__iexact="training").count(), 1)


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------
class ApiEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.cfg = ActivityConfiguration.objects.create(
            activity_name="Training", productive_status=True, category="Productive", display_color="#2E8B7E",
        )
        start = datetime.fromisoformat("2025-10-01T07:00:00+00:00")
        end = datetime.fromisoformat("2025-10-01T09:00:00+00:00")
        ShiftRecord.objects.create(
            date="2025-10-01", start_time=start, end_time=end, duration_hours=2.0,
            activity_reason="Training", activity_config=self.cfg, source_row_hash="hash1",
        )

    def test_dashboard_summary_endpoint_returns_expected_shape(self):
        response = self.client.get("/api/dashboard-summary")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        for key in ("total_hours", "productive_hours", "downtime_hours", "efficiency_score", "record_count"):
            self.assertIn(key, data)

    def test_filter_options_endpoint_reflects_database_state(self):
        response = self.client.get("/api/filter-options")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("Training", data["reasons"])
        self.assertIn("Productive", data["categories"])

    def test_shift_analysis_endpoint_returns_blocks(self):
        response = self.client.get("/api/shift-analysis")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["blocks"]), 1)
        self.assertEqual(data["blocks"][0]["activity_name"], "Training")

    def test_date_range_filter_excludes_out_of_range_records(self):
        response = self.client.get("/api/dashboard-summary?date_from=2025-11-01&date_to=2025-11-30")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["record_count"], 0)

    def test_category_filter_narrows_results(self):
        response = self.client.get("/api/dashboard-summary?category=Productive")
        data = response.json()
        self.assertEqual(data["record_count"], 1)
        response = self.client.get("/api/dashboard-summary?category=Failure")
        data = response.json()
        self.assertEqual(data["record_count"], 0)

    def test_insights_endpoint_returns_list(self):
        response = self.client.get("/api/insights")
        self.assertEqual(response.status_code, 200)
        self.assertIn("insights", response.json())

    def test_breakdown_streaks_endpoint_returns_config(self):
        response = self.client.get("/api/breakdown-streaks")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("streaks", data)
        self.assertIn("config", data)
