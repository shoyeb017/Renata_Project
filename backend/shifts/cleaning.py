"""
shifts.cleaning
================
Data validation and cleaning pipeline. Implements the "Data Quality Module"
required by the spec: detects missing values, incorrect durations, invalid
timestamps (including overnight shifts), and duplicate records, and
produces a structured report of what it did.

Design note on assumptions (also documented in README):
  - A record is considered UNRECOVERABLE (dropped) only if, after every
    repair attempt below, it is still missing a parseable date, OR missing
    both start and end time (no way to infer one from the other).
  - If only START or only END is missing, but HOURS is present and valid,
    we DERIVE the missing timestamp from the other timestamp + HOURS. This
    keeps a record usable rather than discarding real shift time data.
  - If DAY_DATE is malformed (e.g. "2025-15-55", an impossible month/day)
    but a valid START timestamp exists, we derive the date from START
    instead of dropping the row.
  - END < START is treated as an overnight shift (END rolled to next day)
    UNLESS the gap implied is implausibly large (>16h), in which case the
    record is flagged invalid rather than guessed at.
  - HOURS vs (END-START) mismatches beyond a small tolerance (0.05h, i.e.
    3 minutes, to absorb rounding) are recalculated from the timestamps,
    since timestamps are the more granular, less error-prone source.
  - Negative or non-numeric HOURS are always recalculated from timestamps
    when timestamps are valid; if timestamps are also invalid, the row is
    dropped as invalid.
  - Exact duplicate rows (same date, start, end, reason) are removed,
    keeping the first occurrence.
"""
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

import pandas as pd

OVERNIGHT_MAX_PLAUSIBLE_HOURS = 16
DURATION_TOLERANCE_HOURS = 0.05


@dataclass
class CleaningReport:
    total_records: int = 0
    invalid_records: int = 0
    duplicates_removed: int = 0
    missing_values_handled: int = 0
    duration_mismatches_fixed: int = 0
    final_clean_records: int = 0
    issues: list = field(default_factory=list)

    def log(self, row_index, message):
        self.issues.append({"row": int(row_index), "issue": message})

    def as_dict(self):
        return {
            "total_records": self.total_records,
            "invalid_records": self.invalid_records,
            "duplicates_removed": self.duplicates_removed,
            "missing_values_handled": self.missing_values_handled,
            "duration_mismatches_fixed": self.duration_mismatches_fixed,
            "final_clean_records": self.final_clean_records,
        }


def _parse_timestamp(value) -> Optional[datetime]:
    if value is None:
        return None
    text = str(value).strip()
    if text == "" or text.lower() == "nan":
        return None
    try:
        ts = pd.to_datetime(text, utc=True, errors="raise")
        return ts.to_pydatetime()
    except (ValueError, TypeError):
        return None


def _parse_date(value) -> Optional[datetime]:
    if value is None:
        return None
    text = str(value).strip()
    if text == "" or text.lower() == "nan":
        return None
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    try:
        ts = pd.to_datetime(text, errors="raise")
        return ts.to_pydatetime().replace(tzinfo=None)
    except (ValueError, TypeError):
        return None


def _parse_hours(value) -> Optional[float]:
    if value is None:
        return None
    try:
        f = float(value)
        if pd.isna(f):
            return None
        return f
    except (ValueError, TypeError):
        return None


def _row_hash(date_val, start, end, reason) -> str:
    key = f"{date_val}|{start}|{end}|{(reason or '').strip().lower()}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def clean_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, CleaningReport]:
    """
    Takes a raw DataFrame with columns DAY_DATE, START, END, HOURS, REASON
    and returns (clean_dataframe, CleaningReport).

    The output dataframe has columns:
      date (datetime.date), start_time (datetime), end_time (datetime),
      duration_hours (float), activity_reason (str),
      duration_was_recalculated (bool), source_row_hash (str)
    """
    report = CleaningReport(total_records=len(df))
    cleaned_rows = []
    seen_hashes = set()

    for idx, raw in df.iterrows():
        missing_in_row = False

        reason = raw.get("REASON")
        reason = str(reason).strip() if reason is not None and str(reason).strip().lower() not in ("", "nan") else None
        if reason is None:
            reason = "Unspecified"
            missing_in_row = True
            report.log(idx, "Missing REASON; set to 'Unspecified'.")

        start_dt = _parse_timestamp(raw.get("START"))
        end_dt = _parse_timestamp(raw.get("END"))
        hours = _parse_hours(raw.get("HOURS"))
        date_val = _parse_date(raw.get("DAY_DATE"))

        if start_dt is None:
            missing_in_row = True
            report.log(idx, "Missing/invalid START timestamp.")
        if end_dt is None:
            missing_in_row = True
            report.log(idx, "Missing/invalid END timestamp.")

        # Try to derive a missing timestamp from the other + HOURS.
        if start_dt is None and end_dt is not None and hours is not None and hours > 0:
            start_dt = end_dt - timedelta(hours=hours)
            report.log(idx, "Derived missing START from END - HOURS.")
        elif end_dt is None and start_dt is not None and hours is not None and hours > 0:
            end_dt = start_dt + timedelta(hours=hours)
            report.log(idx, "Derived missing END from START + HOURS.")

        if start_dt is None or end_dt is None:
            report.invalid_records += 1
            report.log(idx, "Dropped: could not establish both START and END.")
            continue

        # Handle overnight / END-before-START.
        if end_dt < start_dt:
            implied_overnight_hours = ((end_dt + timedelta(days=1)) - start_dt).total_seconds() / 3600
            if implied_overnight_hours <= OVERNIGHT_MAX_PLAUSIBLE_HOURS:
                end_dt = end_dt + timedelta(days=1)
                report.log(idx, "END was before START; treated as an overnight shift (+1 day).")
            else:
                report.invalid_records += 1
                report.log(idx, "Dropped: END before START with implausible overnight gap.")
                continue

        computed_hours = round((end_dt - start_dt).total_seconds() / 3600, 4)
        duration_recalculated = False
        if hours is None or hours <= 0 or abs(hours - computed_hours) > DURATION_TOLERANCE_HOURS:
            hours = computed_hours
            duration_recalculated = True
            report.duration_mismatches_fixed += 1
            report.log(idx, f"HOURS mismatched/invalid; recalculated to {computed_hours} from timestamps.")

        if date_val is None:
            # Fall back to the date implied by the (validated) start time.
            date_val = start_dt
            missing_in_row = True
            report.log(idx, "Missing/invalid DAY_DATE; derived from START timestamp.")

        if missing_in_row:
            report.missing_values_handled += 1

        final_date = date_val.date()
        row_hash = _row_hash(final_date, start_dt.isoformat(), end_dt.isoformat(), reason)
        if row_hash in seen_hashes:
            report.duplicates_removed += 1
            report.log(idx, "Dropped: exact duplicate of a previously seen record.")
            continue
        seen_hashes.add(row_hash)

        cleaned_rows.append({
            "date": final_date,
            "start_time": start_dt,
            "end_time": end_dt,
            "duration_hours": hours,
            "activity_reason": reason,
            "duration_was_recalculated": duration_recalculated,
            "source_row_hash": row_hash,
        })

    report.final_clean_records = len(cleaned_rows)
    clean_df = pd.DataFrame(cleaned_rows)
    return clean_df, report
