from shifts.models import ShiftRecord
from config_app.loader import get_or_register_activity
from datetime import datetime


def load_data():

    rows = [
        # your csv loading here
    ]

    records = []

    for row in rows:

        activity = get_or_register_activity(
            row["REASON"]
        )

        records.append(
            ShiftRecord(
                date=row["DATE"],
                start_time=row["START_TIME"],
                end_time=row["END_TIME"],
                duration_hours=float(row["HOURS"]),
                activity_reason=row["REASON"],
                activity_config=activity,
                duration_was_recalculated=False,
                source_row_hash="some_unique_hash_here"
            )
        )

    ShiftRecord.objects.bulk_create(records)