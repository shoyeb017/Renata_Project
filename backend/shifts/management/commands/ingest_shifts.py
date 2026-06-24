import json
import os
from pathlib import Path

import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from config_app.loader import get_or_register_activity
from shifts.cleaning import clean_dataframe
from shifts.models import ShiftRecord, DataQualityReport


class Command(BaseCommand):
    help = (
        "Ingest the shift dataset CSV (path from DATASET_PATH env var, or "
        "--path override), clean it, auto-register any unknown activity "
        "categories, and load it into the database. Idempotent: re-running "
        "will not create duplicate ShiftRecord rows because of the unique "
        "source_row_hash, and will not duplicate ActivityConfiguration rows "
        "for activities already known."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            type=str,
            default=None,
            help="Override path to the dataset CSV. Defaults to DATASET_PATH env var.",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete all existing ShiftRecord rows before ingesting (full refresh).",
        )

    def handle(self, *args, **options):
        dataset_path = options["path"] or os.environ.get("DATASET_PATH") or str(
            Path(settings.BASE_DIR) / "data" / "shift_data.csv"
        )
        dataset_path = Path(dataset_path)

        if not dataset_path.exists():
            self.stderr.write(self.style.ERROR(f"Dataset not found at: {dataset_path}"))
            return

        self.stdout.write(f"Reading dataset from: {dataset_path}")
        df = pd.read_csv(dataset_path, dtype=str)

        clean_df, report = clean_dataframe(df)

        if options["reset"]:
            deleted, _ = ShiftRecord.objects.all().delete()
            self.stdout.write(f"--reset passed: deleted {deleted} existing ShiftRecord rows.")

        created_count = 0
        skipped_existing = 0
        newly_registered_activities = set()

        with transaction.atomic():
            for _, row in clean_df.iterrows():
                activity_config = get_or_register_activity(row["activity_reason"])
                if activity_config.is_auto_registered:
                    newly_registered_activities.add(activity_config.activity_name)

                _, created = ShiftRecord.objects.get_or_create(
                    source_row_hash=row["source_row_hash"],
                    defaults={
                        "date": row["date"],
                        "start_time": row["start_time"],
                        "end_time": row["end_time"],
                        "duration_hours": row["duration_hours"],
                        "activity_reason": row["activity_reason"],
                        "activity_config": activity_config,
                        "duration_was_recalculated": bool(row["duration_was_recalculated"]),
                    },
                )
                if created:
                    created_count += 1
                else:
                    skipped_existing += 1

            DataQualityReport.objects.create(
                total_records=report.total_records,
                invalid_records=report.invalid_records,
                duplicates_removed=report.duplicates_removed,
                missing_values_handled=report.missing_values_handled,
                duration_mismatches_fixed=report.duration_mismatches_fixed,
                final_clean_records=report.final_clean_records,
                details_json=json.dumps(report.issues),
            )

        self.stdout.write(self.style.SUCCESS(
            f"Ingestion complete.\n"
            f"  Total raw records:        {report.total_records}\n"
            f"  Invalid (dropped):        {report.invalid_records}\n"
            f"  Duplicates removed:       {report.duplicates_removed}\n"
            f"  Missing values handled:   {report.missing_values_handled}\n"
            f"  Duration mismatches fixed:{report.duration_mismatches_fixed}\n"
            f"  Final clean records:      {report.final_clean_records}\n"
            f"  New ShiftRecord rows:      {created_count}\n"
            f"  Already existed (skipped):{skipped_existing}\n"
            f"  Newly auto-registered activities: {sorted(newly_registered_activities) or 'none'}"
        ))
