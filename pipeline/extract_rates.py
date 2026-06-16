"""
EXTRACT stage: pull an interest-rate history.

Tries the live FRED CSV endpoint (no API key required). If the network is
unavailable (offline dev, CI without egress, rate limits), it falls back to a
committed sample CSV so the pipeline is always runnable and deterministic.

Output: data/raw/interest_rates.csv  (columns: date, rate_pct)
"""

from __future__ import annotations

import io

from loguru import logger
import pandas as pd
import requests

from pipeline import config


def _from_fred(series: str, timeout: int = 15) -> pd.DataFrame:
    url = config.FRED_CSV_URL.format(series=series)
    logger.info("Fetching rate series '{}' from FRED...", series)
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    df = pd.read_csv(io.StringIO(resp.text))
    # FRED returns columns: DATE, <SERIES_ID>
    df.columns = ["date", "rate_pct"]
    return df


def _from_sample() -> pd.DataFrame:
    logger.warning("Falling back to committed sample data: {}", config.SAMPLE_RATES_CSV)
    df = pd.read_csv(config.SAMPLE_RATES_CSV)
    df.columns = ["date", "rate_pct"]
    return df


def extract(series: str | None = None, offline: bool = False) -> pd.DataFrame:
    """Return a cleaned rate history and write it to RATES_RAW_CSV."""
    config.ensure_dirs()
    series = series or config.FRED_SERIES_ID

    if offline:
        df = _from_sample()
    else:
        try:
            df = _from_fred(series)
        except Exception as exc:  # network/parse errors -> deterministic fallback
            logger.warning("Live fetch failed ({}); using sample data.", exc)
            df = _from_sample()

    # --- clean ---
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["rate_pct"] = pd.to_numeric(df["rate_pct"], errors="coerce")
    df = df.dropna(subset=["date", "rate_pct"]).sort_values("date").reset_index(drop=True)

    df.to_csv(config.RATES_RAW_CSV, index=False)
    logger.success(
        "Extracted {} rows -> {} (range {} to {})",
        len(df),
        config.RATES_RAW_CSV,
        df["date"].min().date(),
        df["date"].max().date(),
    )
    return df


if __name__ == "__main__":
    extract()
