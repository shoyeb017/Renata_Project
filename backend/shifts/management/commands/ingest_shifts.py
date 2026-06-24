import os
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from shifts.ingestion import ingest_csv_path
from shifts.models import Dataset


class Command(BaseCommand):
    help = (
        "Ingest a shift dataset CSV (path from DATASET_PATH env var, or "
        "--path override) as a new Dataset, clean it, auto-register any "
        "unknown activity categories, and load it into the database as "
        "the active dataset. This is the same code path the dashboard's "
        "upload feature uses, so a CLI-ingested dataset and an "
        "uploaded-via-UI dataset are held to identical standards."
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
            help="Delete ALL existing datasets and their records before ingesting "
                 "(full refresh, including upload history).",
        )
        parser.add_argument(
            "--name",
            type=str,
            default=None,
            help="Display name for this dataset. Defaults to the file name.",
        )

    def handle(self, *args, **options):
        dataset_path = options["path"] or os.environ.get("DATASET_PATH") or str(
            Path(settings.BASE_DIR) / "data" / "shift_data.csv"
        )
        dataset_path = Path(dataset_path)

        if not dataset_path.exists():
            self.stderr.write(self.style.ERROR(f"Dataset not found at: {dataset_path}"))
            return

        if options["reset"]:
            deleted, _ = Dataset.objects.all().delete()
            self.stdout.write(f"--reset passed: deleted {deleted} existing dataset(s) and their records.")

        dataset_name = options["name"] or dataset_path.name
        self.stdout.write(f"Reading dataset from: {dataset_path}")

        result = ingest_csv_path(str(dataset_path), dataset_name=dataset_name, source="default", activate=True)
        report = result["report"]

        self.stdout.write(self.style.SUCCESS(
            f"Ingestion complete. Dataset: '{result['dataset_name']}' (id={result['dataset_id']}, active={result['is_active']})\n"
            f"  Total raw records:         {report['total_records']}\n"
            f"  Invalid (dropped):         {report['invalid_records']}\n"
            f"  Duplicates removed:        {report['duplicates_removed']}\n"
            f"  Missing values handled:    {report['missing_values_handled']}\n"
            f"  Duration mismatches fixed: {report['duration_mismatches_fixed']}\n"
            f"  Final clean records:       {report['final_clean_records']}\n"
            f"  Zero-hour anomalies:       {report['zero_hour_count']}\n"
            f"  Negative-hour anomalies:   {report['negative_hour_count']}\n"
            f"  Statistical outliers:      {report['outlier_hour_count']}\n"
            f"  Newly auto-registered activities: {result['new_activities_registered'] or 'none'}"
        ))
