"""
shifts.ingestion
=================
Core ingestion logic, factored out so it can be called identically from:
  - the `ingest_shifts` management command (CLI / startup seeding)
  - the `/api/datasets/upload` endpoint (runtime upload from the dashboard)

Both paths produce the same guarantees: clean the data, auto-register any
unknown activity categories, persist ShiftRecords under a Dataset, and
write a DataQualityReport - so a CSV uploaded through the UI is held to
exactly the same standard as the bundled default dataset.
"""
import json

import pandas as pd
from django.db import transaction

from config_app.loader import get_or_register_activity
from .cleaning import clean_dataframe
from .models import Dataset, ShiftRecord, DataQualityReport


def ingest_dataframe(df: pd.DataFrame, dataset_name: str, source: str, activate: bool = True) -> dict:
    """
    Cleans `df`, creates a new Dataset row, persists its ShiftRecords and
    a DataQualityReport, and (by default) makes it the active dataset that
    the API serves. Returns a summary dict.

    Each upload becomes its OWN Dataset (never merged with a previous
    one), so switching datasets is just flipping which Dataset row has
    is_active=True - previous uploads are kept, not destroyed, in case
    a user wants to revert.
    """
    clean_df, report = clean_dataframe(df)

    newly_registered_activities = set()

    with transaction.atomic():
        if activate:
            Dataset.objects.filter(is_active=True).update(is_active=False)

        dataset = Dataset.objects.create(
            name=dataset_name,
            source=source,
            is_active=activate,
            row_count=len(clean_df),
        )

        shift_records = []
        for _, row in clean_df.iterrows():
            activity_config = get_or_register_activity(row["activity_reason"])
            if activity_config.is_auto_registered:
                newly_registered_activities.add(activity_config.activity_name)

            shift_records.append(ShiftRecord(
                dataset=dataset,
                date=row["date"],
                start_time=row["start_time"],
                end_time=row["end_time"],
                duration_hours=row["duration_hours"],
                activity_reason=row["activity_reason"],
                activity_config=activity_config,
                duration_was_recalculated=bool(row["duration_was_recalculated"]),
                source_row_hash=row["source_row_hash"],
            ))
        ShiftRecord.objects.bulk_create(shift_records)

        quality_report = DataQualityReport.objects.create(
            dataset=dataset,
            total_records=report.total_records,
            invalid_records=report.invalid_records,
            duplicates_removed=report.duplicates_removed,
            missing_values_handled=report.missing_values_handled,
            duration_mismatches_fixed=report.duration_mismatches_fixed,
            final_clean_records=report.final_clean_records,
            zero_hour_count=report.zero_hour_count,
            negative_hour_count=report.negative_hour_count,
            outlier_hour_count=report.outlier_hour_count,
            details_json=json.dumps(report.issues),
        )

    return {
        "dataset_id": dataset.id,
        "dataset_name": dataset.name,
        "is_active": dataset.is_active,
        "report": report.as_dict(),
        "new_activities_registered": sorted(newly_registered_activities),
        "quality_report_id": quality_report.id,
    }


def ingest_csv_path(path: str, dataset_name: str, source: str, activate: bool = True) -> dict:
    df = pd.read_csv(path, dtype=str)
    return ingest_dataframe(df, dataset_name=dataset_name, source=source, activate=activate)


def ingest_csv_file(file_obj, dataset_name: str, source: str = "upload", activate: bool = True) -> dict:
    """Accepts a Django UploadedFile (or any file-like object) directly."""
    df = pd.read_csv(file_obj, dtype=str)
    return ingest_dataframe(df, dataset_name=dataset_name, source=source, activate=activate)
