"""
Tests for the data cleaning pipeline, analytics engine, dataset/upload
flow, and API layer. Run with: python manage.py test
"""
import io
from datetime import date, datetime

import pandas as pd
from django.test import TestCase
from rest_framework.test import APIClient
from django.core.files.uploadedfile import SimpleUploadedFile

from config_app.models import ActivityConfiguration
from .cleaning import clean_dataframe
from .models import ShiftRecord, Dataset, DataQualityReport
from .ingestion import ingest_dataframe
from .analytics import (
    compute_dashboard_summary,
    compute_breakdown_streaks,
    compute_activity_distribution,
    compute_data_quality_report,
)
from .insights import generate_insights

DEFAULT_SEVERITY_THRESHOLDS = {"critical": 8, "high": 5, "medium": 2}


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
        self.assertEqual(report.missing_values_handled, 1)

    def test_overnight_shift_end_before_start_is_handled(self):
        df = self._df([
            ["10/4/2025", "2025-10-04T22:00:00Z", "2025-10-05T02:00:00Z", "4", "Maintenance"],
        ])
        clean_df, report = clean_dataframe(df)
        self.assertEqual(len(clean_df), 1)
        self.assertEqual(clean_df.iloc[0]["duration_hours"], 4.0)

    def test_implausible_overnight_gap_is_dropped(self):
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
            ["10/2/2025", None, None, "1", "Training"],
        ]
        df = self._df(rows)
        clean_df, report = clean_dataframe(df)
        self.assertEqual(report.total_records, 2)
        self.assertEqual(report.final_clean_records, len(clean_df))
        self.assertEqual(
            report.final_clean_records,
            report.total_records - report.invalid_records - report.duplicates_removed,
        )

    def test_zero_and_negative_hour_anomalies_are_counted(self):
        rows = [
            ["10/1/2025", "2025-10-01T07:00:00Z", "2025-10-01T07:00:00Z", "0", "Idle"],
            ["10/2/2025", "2025-10-02T07:00:00Z", "2025-10-02T09:00:00Z", "-2", "Breakdown"],
        ]
        df = self._df(rows)
        clean_df, report = clean_dataframe(df)
        self.assertEqual(report.zero_hour_count, 1)
        self.assertEqual(report.negative_hour_count, 1)

    def test_outlier_detection_flags_top_5_percent_of_durations(self):
        # 19 short shifts + 1 very long one -> the long one should be
        # flagged as a 95th-percentile outlier.
        rows = []
        for i in range(19):
            rows.append([f"10/{i+1}/2025", f"2025-10-{i+1:02d}T07:00:00Z", f"2025-10-{i+1:02d}T08:00:00Z", "1", "Training"])
        rows.append(["10/20/2025", "2025-10-20T07:00:00Z", "2025-10-20T20:00:00Z", "13", "Breakdown"])
        df = self._df(rows)
        clean_df, report = clean_dataframe(df)
        self.assertGreaterEqual(report.outlier_hour_count, 1)


# ---------------------------------------------------------------------------
# Analytics engine tests
# ---------------------------------------------------------------------------
class AnalyticsEngineTests(TestCase):
    def setUp(self):
        self.dataset = Dataset.objects.create(name="test-dataset", source="upload", is_active=True)
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
            dataset=self.dataset,
            date=date_str,
            start_time=start,
            end_time=end,
            duration_hours=(end - start).total_seconds() / 3600,
            activity_reason=reason,
            activity_config=cfg,
            source_row_hash=f"{date_str}{start_str}{end_str}{reason}",
        )

    def test_dashboard_summary_efficiency_calculation(self):
        qs = ShiftRecord.objects.filter(dataset=self.dataset)
        summary = compute_dashboard_summary(qs)
        self.assertEqual(summary["total_hours"], 4.0)
        self.assertEqual(summary["productive_hours"], 2.0)
        self.assertEqual(summary["efficiency_score"], 50.0)

    def test_dashboard_summary_with_no_records(self):
        summary = compute_dashboard_summary(ShiftRecord.objects.none())
        self.assertEqual(summary["total_hours"], 0.0)
        self.assertEqual(summary["efficiency_score"], 0.0)

    def test_activity_distribution_percentages_sum_to_100(self):
        qs = ShiftRecord.objects.filter(dataset=self.dataset)
        dist = compute_activity_distribution(qs)
        total_pct = sum(d["percentage"] for d in dist)
        self.assertAlmostEqual(total_pct, 100.0, places=1)

    def test_breakdown_streak_requires_minimum_events(self):
        qs = ShiftRecord.objects.filter(dataset=self.dataset)
        streaks = compute_breakdown_streaks(qs, min_events=3, min_hours=1, max_gap_hours=4,
                                             severity_thresholds=DEFAULT_SEVERITY_THRESHOLDS)
        self.assertEqual(streaks, [])

    def test_breakdown_streak_detected_when_thresholds_met(self):
        self._make_record("2025-10-01", "11:30", "13:00", self.failure_cfg, "Breakdown")
        self._make_record("2025-10-01", "13:30", "15:00", self.failure_cfg, "Breakdown")
        qs = ShiftRecord.objects.filter(dataset=self.dataset)
        streaks = compute_breakdown_streaks(qs, min_events=3, min_hours=1, max_gap_hours=4,
                                             severity_thresholds=DEFAULT_SEVERITY_THRESHOLDS)
        self.assertEqual(len(streaks), 1)
        self.assertEqual(streaks[0]["event_count"], 3)
        self.assertIn("severity", streaks[0])
        self.assertIn(streaks[0]["severity"], ("Low", "Medium", "High", "Critical"))

    def test_breakdown_streak_broken_by_large_gap(self):
        self._make_record("2025-10-05", "09:00", "10:00", self.failure_cfg, "Breakdown")
        self._make_record("2025-10-05", "20:00", "21:00", self.failure_cfg, "Breakdown")
        qs = ShiftRecord.objects.filter(dataset=self.dataset)
        streaks = compute_breakdown_streaks(qs, min_events=2, min_hours=0.5, max_gap_hours=4,
                                             severity_thresholds=DEFAULT_SEVERITY_THRESHOLDS)
        for streak in streaks:
            self.assertLess(streak["event_count"], 3)

    def test_breakdown_streak_duration_days_and_avg_per_day(self):
        # A streak spanning two calendar days.
        self._make_record("2025-10-02", "08:00", "12:00", self.failure_cfg, "Breakdown")
        qs = ShiftRecord.objects.filter(dataset=self.dataset)
        streaks = compute_breakdown_streaks(qs, min_events=1, min_hours=0.5, max_gap_hours=2,
                                             severity_thresholds=DEFAULT_SEVERITY_THRESHOLDS)
        for s in streaks:
            self.assertEqual(s["avg_hours_per_day"], round(s["total_hours"] / s["duration_days"], 2))

    def test_insights_are_generated_from_data_and_include_severity(self):
        qs = ShiftRecord.objects.filter(dataset=self.dataset)
        insights = generate_insights(qs)
        self.assertGreaterEqual(len(insights), 1)
        for insight in insights:
            self.assertIn("title", insight)
            self.assertIn("metric", insight)
            self.assertIn("text", insight)
            self.assertIn("action", insight)
            self.assertIn("severity", insight)
            self.assertIn(insight["severity"], ("Low", "Medium", "High", "Critical"))
            # Every insight's text must reference at least one number,
            # proving it's derived from computed data, not static text.
            self.assertTrue(any(ch.isdigit() for ch in insight["text"]))

    def test_data_quality_report_shape(self):
        qs = ShiftRecord.objects.filter(dataset=self.dataset)
        report = DataQualityReport.objects.create(
            dataset=self.dataset, total_records=2, invalid_records=0, duplicates_removed=0,
            missing_values_handled=0, duration_mismatches_fixed=0, final_clean_records=2,
            zero_hour_count=0, negative_hour_count=0, outlier_hour_count=0,
        )
        result = compute_data_quality_report(qs, report)
        for key in ("data_validity_pct", "total_records", "valid_records", "invalid_records",
                    "total_hours", "avg_shift_duration_hours", "category_count", "anomalies"):
            self.assertIn(key, result)
        self.assertEqual(result["data_validity_pct"], 100.0)
        self.assertEqual(result["category_count"], 2)


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
# Dataset / ingestion service tests
# ---------------------------------------------------------------------------
class IngestionServiceTests(TestCase):
    def _sample_df(self):
        return pd.DataFrame([
            {"DAY_DATE": "10/1/2025", "START": "2025-10-01T07:00:00Z", "END": "2025-10-01T09:00:00Z", "HOURS": "2", "REASON": "Training"},
            {"DAY_DATE": "10/2/2025", "START": "2025-10-02T07:00:00Z", "END": "2025-10-02T09:00:00Z", "HOURS": "2", "REASON": "Breakdown"},
        ])

    def test_ingest_dataframe_creates_active_dataset_and_records(self):
        result = ingest_dataframe(self._sample_df(), dataset_name="sample.csv", source="upload")
        dataset = Dataset.objects.get(id=result["dataset_id"])
        self.assertTrue(dataset.is_active)
        self.assertEqual(ShiftRecord.objects.filter(dataset=dataset).count(), 2)

    def test_ingesting_new_dataset_deactivates_previous_one(self):
        first = ingest_dataframe(self._sample_df(), dataset_name="first.csv", source="upload")
        second = ingest_dataframe(self._sample_df(), dataset_name="second.csv", source="upload")
        first_dataset = Dataset.objects.get(id=first["dataset_id"])
        second_dataset = Dataset.objects.get(id=second["dataset_id"])
        self.assertFalse(first_dataset.is_active)
        self.assertTrue(second_dataset.is_active)
        # Previous dataset's records are preserved, not deleted.
        self.assertEqual(ShiftRecord.objects.filter(dataset=first_dataset).count(), 2)

    def test_ingestion_creates_quality_report(self):
        result = ingest_dataframe(self._sample_df(), dataset_name="sample.csv", source="upload")
        self.assertTrue(DataQualityReport.objects.filter(id=result["quality_report_id"]).exists())


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------
class ApiEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.dataset = Dataset.objects.create(name="api-test-dataset", source="upload", is_active=True)
        self.cfg = ActivityConfiguration.objects.create(
            activity_name="Training", productive_status=True, category="Productive", display_color="#2E8B7E",
        )
        self.failure_cfg = ActivityConfiguration.objects.create(
            activity_name="Breakdown", productive_status=False, category="Failure", display_color="#C44536",
        )
        start = datetime.fromisoformat("2025-10-01T07:00:00+00:00")
        end = datetime.fromisoformat("2025-10-01T09:00:00+00:00")
        ShiftRecord.objects.create(
            dataset=self.dataset, date="2025-10-01", start_time=start, end_time=end, duration_hours=2.0,
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

    def test_breakdown_streaks_endpoint_returns_config_and_timeline(self):
        response = self.client.get("/api/breakdown-streaks")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("streaks", data)
        self.assertIn("timeline", data)
        self.assertIn("config", data)

    def test_breakdown_streaks_endpoint_ignores_filters(self):
        """
        Breakdown Streaks must reflect the WHOLE active dataset, regardless
        of any filter query params passed - this is the key behavioral
        requirement distinguishing it from the filter-aware panels.
        """
        ShiftRecord.objects.create(
            dataset=self.dataset, date="2025-10-05", start_time=datetime.fromisoformat("2025-10-05T08:00:00+00:00"),
            end_time=datetime.fromisoformat("2025-10-05T12:00:00+00:00"), duration_hours=4.0,
            activity_reason="Breakdown", activity_config=self.failure_cfg, source_row_hash="hash2",
        )
        unfiltered = self.client.get("/api/breakdown-streaks").json()
        filtered = self.client.get("/api/breakdown-streaks?date_from=2099-01-01").json()
        self.assertEqual(unfiltered["streaks"], filtered["streaks"])
        self.assertEqual(unfiltered["timeline"], filtered["timeline"])

    def test_data_quality_report_endpoint_ignores_filters(self):
        unfiltered = self.client.get("/api/data-quality-report").json()
        filtered = self.client.get("/api/data-quality-report?date_from=2099-01-01").json()
        self.assertEqual(unfiltered, filtered)
        self.assertIn("anomalies", unfiltered)

    def test_list_datasets_endpoint(self):
        response = self.client.get("/api/datasets")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreaterEqual(len(data["datasets"]), 1)

    def test_upload_dataset_endpoint_accepts_csv_and_activates_it(self):
        csv_content = (
            "DAY_DATE,START,END,HOURS,REASON\n"
            "10/10/2025,2025-10-10T07:00:00Z,2025-10-10T09:00:00Z,2,Training\n"
        )
        uploaded = SimpleUploadedFile("new_data.csv", csv_content.encode("utf-8"), content_type="text/csv")
        response = self.client.post("/api/datasets/upload", {"file": uploaded}, format="multipart")
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertTrue(data["is_active"])

        # The previously active dataset's data should no longer be served
        # by default since the new upload is now active.
        summary = self.client.get("/api/dashboard-summary").json()
        self.assertEqual(summary["record_count"], 1)

    def test_upload_dataset_rejects_non_csv(self):
        uploaded = SimpleUploadedFile("not_a_csv.txt", b"hello", content_type="text/plain")
        response = self.client.post("/api/datasets/upload", {"file": uploaded}, format="multipart")
        self.assertEqual(response.status_code, 400)

    def test_activate_dataset_endpoint_switches_active_dataset(self):
        other_dataset = Dataset.objects.create(name="other.csv", source="upload", is_active=False)
        response = self.client.post(f"/api/datasets/{other_dataset.id}/activate")
        self.assertEqual(response.status_code, 200)
        other_dataset.refresh_from_db()
        self.dataset.refresh_from_db()
        self.assertTrue(other_dataset.is_active)
        self.assertFalse(self.dataset.is_active)
