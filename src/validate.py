"""Validation and cleaning rules for raw tourism visit records.

Pure pandas functions with no AWS dependency, so they can be unit tested on
their own and reused outside Lambda.
"""
from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS = [
    "visit_id",
    "user_id",
    "attraction_id",
    "attraction_type",
    "country",
    "visit_year",
    "visit_month",
    "visit_mode",
    "rating",
]
VALID_VISIT_MODES = {"Business", "Couples", "Family", "Friends", "Solo"}
RATING_MIN, RATING_MAX = 1, 5


def validate_and_clean(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Return (clean_df, report).

    Rules (each rejected row is counted under exactly one reason, checked in
    this order):
      1. missing_required_value : any required column is null/blank
      2. duplicate_visit_id     : visit_id already seen (first one is kept)
      3. invalid_rating         : rating not an integer in [1, 5]
      4. invalid_month          : visit_month not in 1..12
      5. invalid_visit_mode     : visit_mode not in the allowed set
    """
    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    work = df[REQUIRED_COLUMNS].copy()
    rows_in = len(work)
    reasons: dict[str, int] = {}

    def drop(mask: pd.Series, reason: str) -> None:
        nonlocal work
        reasons[reason] = int(mask.sum())
        work = work[~mask]

    # Treat blank strings as missing.
    work = work.replace(r"^\s*$", pd.NA, regex=True)

    drop(work.isna().any(axis=1), "missing_required_value")
    drop(work.duplicated(subset="visit_id", keep="first"), "duplicate_visit_id")

    rating = pd.to_numeric(work["rating"], errors="coerce")
    bad_rating = rating.isna() | (rating % 1 != 0) | ~rating.between(RATING_MIN, RATING_MAX)
    drop(bad_rating, "invalid_rating")

    month = pd.to_numeric(work["visit_month"], errors="coerce")
    drop(month.isna() | ~month.between(1, 12), "invalid_month")

    work["visit_mode"] = work["visit_mode"].astype(str).str.strip().str.title()
    drop(~work["visit_mode"].isin(VALID_VISIT_MODES), "invalid_visit_mode")

    work["rating"] = pd.to_numeric(work["rating"]).astype(int)
    work["visit_month"] = pd.to_numeric(work["visit_month"]).astype(int)
    work["visit_year"] = pd.to_numeric(work["visit_year"]).astype(int)
    work["attraction_type"] = work["attraction_type"].astype(str).str.strip()
    work["country"] = work["country"].astype(str).str.strip()

    rows_out = len(work)
    report = {
        "rows_in": rows_in,
        "rows_out": rows_out,
        "rows_rejected": rows_in - rows_out,
        "rejected_by_reason": reasons,
        "pass_rate": round(rows_out / rows_in, 4) if rows_in else 0.0,
    }
    return work.reset_index(drop=True), report
