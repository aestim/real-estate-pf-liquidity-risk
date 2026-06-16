"""
CALIBRATE stage: derive model parameters from the extracted rate history.

The simulation engine needs triangular (min, mode, max) interest-rate inputs.
Instead of hard-coding them, we derive them from the macro rate anchor:

    anchor_min  = 10th percentile of the rate history
    anchor_mode = median
    anchor_max  = 90th percentile

then apply a documented PF lending spread for each financing phase:

    pre_refi  = anchor + PF_SPREAD_PRE_REFI   (construction-phase premium)
    post_refi = anchor + PF_SPREAD_POST_REFI  (facility-loan step-down)

Output: data/processed/calibrated_params.json
"""

from __future__ import annotations

from datetime import datetime, timezone
import json

from loguru import logger
import pandas as pd

from pipeline import config


def _triangle(series: pd.Series, spread: float, floor: float = 0.01) -> tuple[float, float, float]:
    lo = max(floor, round(series.quantile(0.10) / 100 + spread, 4))
    mode = max(floor, round(series.quantile(0.50) / 100 + spread, 4))
    hi = max(floor, round(series.quantile(0.90) / 100 + spread, 4))
    # guarantee min <= mode <= max even with odd spreads
    lo, mode, hi = sorted((lo, mode, hi))
    return (lo, mode, hi)


def calibrate(rates: pd.DataFrame | None = None) -> dict:
    config.ensure_dirs()
    if rates is None:
        rates = pd.read_csv(config.RATES_RAW_CSV)

    s = pd.to_numeric(rates["rate_pct"], errors="coerce").dropna()
    if s.empty:
        raise ValueError("No usable rate observations to calibrate from.")

    params = {
        "source_series": config.FRED_SERIES_ID,
        "n_observations": int(s.shape[0]),
        "anchor_median_pct": round(float(s.median()), 3),
        "pre_refi_rate": _triangle(s, config.PF_SPREAD_PRE_REFI),
        "post_refi_rate": _triangle(s, config.PF_SPREAD_POST_REFI),
        "calibrated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }

    config.CALIBRATION_JSON.write_text(json.dumps(params, indent=2))
    logger.success(
        "Calibrated pre_refi={} post_refi={} -> {}",
        params["pre_refi_rate"],
        params["post_refi_rate"],
        config.CALIBRATION_JSON,
    )
    return params


if __name__ == "__main__":
    calibrate()
