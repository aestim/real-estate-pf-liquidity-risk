"""
Data-quality gate for the extracted rate history.

This runs *after* extract and *before* the data is allowed downstream. The point
is to fail fast on bad source data rather than silently feeding garbage into the
model — the kind of check a real ingestion pipeline needs.

Hard failures raise DataQualityError (pipeline stops); soft issues are warned.
"""

from __future__ import annotations

from loguru import logger
import pandas as pd

# Plausible bounds for a Korean short-term market rate (%). CD 91-day has
# historically sat roughly between 0.5% and 6%; we allow a generous 0–30 window
# so the gate catches obvious corruption (negative, 9999, decimals-as-percent)
# without rejecting legitimate rate regimes.
RATE_MIN_PCT = 0.0
RATE_MAX_PCT = 30.0
MIN_ROWS = 12
MAX_NULL_RATIO = 0.05


class DataQualityError(ValueError):
    """Raised when extracted data fails a hard quality check."""


def validate_rates(df: pd.DataFrame) -> dict:
    """Validate the rate history. Raises DataQualityError on hard violations."""
    checks: list[str] = []

    # 1) non-empty / enough history
    if len(df) < MIN_ROWS:
        raise DataQualityError(f"too few rows: {len(df)} < {MIN_ROWS}")
    checks.append(f"row_count>={MIN_ROWS}")

    # 2) required columns present
    missing = {"date", "rate_pct"} - set(df.columns)
    if missing:
        raise DataQualityError(f"missing columns: {missing}")
    checks.append("schema")

    # 3) null ratio
    null_ratio = df["rate_pct"].isna().mean()
    if null_ratio > MAX_NULL_RATIO:
        raise DataQualityError(f"null ratio too high: {null_ratio:.1%}")
    checks.append("null_ratio")

    # 4) value range
    vals = df["rate_pct"].dropna()
    if vals.min() < RATE_MIN_PCT or vals.max() > RATE_MAX_PCT:
        raise DataQualityError(
            f"rate out of bounds [{RATE_MIN_PCT},{RATE_MAX_PCT}]: "
            f"min={vals.min()}, max={vals.max()}"
        )
    checks.append("range")

    # 5) dates unique & sorted (hard) / no large gaps (soft)
    if df["date"].duplicated().any():
        raise DataQualityError("duplicate dates found")
    if not df["date"].is_monotonic_increasing:
        raise DataQualityError("dates not sorted ascending")
    checks.append("dates")

    gap_days = df["date"].diff().dt.days.dropna()
    if not gap_days.empty and gap_days.max() > 45:
        logger.warning("Soft check: largest date gap is {} days", int(gap_days.max()))

    report = {
        "n_rows": len(df),
        "checks_passed": checks,
        "null_ratio": round(float(null_ratio), 4),
    }
    logger.success("Data quality OK: {}", report)
    return report


if __name__ == "__main__":
    from pipeline import config

    validate_rates(pd.read_csv(config.RATES_RAW_CSV, parse_dates=["date"]))
