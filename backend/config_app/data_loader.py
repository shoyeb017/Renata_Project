import pandas as pd
from shifts.models import ShiftRecord
from django.conf import settings


def load_data():
    file_path = settings.DATASET_PATH

    df = pd.read_csv(file_path)

    records = []

    for _, row in df.iterrows():
        records.append(
            ShiftRecord(
                # change these according to your model fields
                reason=row["REASON"],
            )
        )

    ShiftRecord.objects.bulk_create(records)

    return len(records)