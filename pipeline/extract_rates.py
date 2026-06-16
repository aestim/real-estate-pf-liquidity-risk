"""
EXTRACT stage: pull a Korean interest-rate history.

Primary source is the Bank of Korea ECOS API (CD 91-day yield), which is the
closest public proxy for Korean PF / bridge-loan funding cost. The live call
needs a free ECOS API key (env ECOS_API_KEY). When the key or network is
unavailable (offline dev, CI without secrets), it falls back to a committed
sample CSV so the pipeline is always runnable and deterministic.

Output: data/raw/interest_rates.csv  (columns: date, rate_pct)
"""

from __future__ import annotations

from loguru import logger
import pandas as pd
import requests

from pipeline import config
from pipeline.validate import validate_rates


def _from_ecos(api_key: str, timeout: int = 15) -> pd.DataFrame:
    url = config.ECOS_URL.format(
        key=api_key,
        stat=config.ECOS_STAT_CODE,
        cycle=config.ECOS_CYCLE,
        start=config.ECOS_START,
        end=config.ECOS_END,
        item=config.ECOS_ITEM_CODE,
    )
    logger.info("Fetching CD(91-day) from BOK ECOS...")
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    payload = resp.json()

    if "StatisticSearch" not in payload:
        # ECOS returns an error object (e.g., bad key) instead of data
        raise ValueError(f"ECOS error response: {payload}")

    rows = payload["StatisticSearch"]["row"]
    df = pd.DataFrame(rows)[["TIME", "DATA_VALUE"]]
    # TIME is YYYYMMDD (daily) or YYYYMM (monthly) depending on the series cycle.
    time_str = df["TIME"].astype(str)
    fmt = "%Y%m%d" if time_str.str.len().max() == 8 else "%Y%m"
    df["date"] = pd.to_datetime(time_str, format=fmt, errors="coerce")
    df["rate_pct"] = pd.to_numeric(df["DATA_VALUE"], errors="coerce")
    return df[["date", "rate_pct"]]


def list_items(stat_code: str | None = None, timeout: int = 15) -> pd.DataFrame:
    """Discovery helper: list available item codes/names for an ECOS stat table.

    Use this to confirm the right ITEM_CODE/CYCLE when a search returns
    'INFO-200 해당하는 데이터가 없습니다'.
    """
    stat_code = stat_code or config.ECOS_STAT_CODE
    if not config.ECOS_API_KEY:
        raise RuntimeError("ECOS_API_KEY not set (put it in .env).")
    url = config.ECOS_ITEMLIST_URL.format(key=config.ECOS_API_KEY, stat=stat_code)
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    payload = resp.json()
    if "StatisticItemList" not in payload:
        raise ValueError(f"ECOS error response: {payload}")
    rows = payload["StatisticItemList"]["row"]
    cols = [
        c for c in ("ITEM_CODE", "ITEM_NAME", "CYCLE", "START_TIME", "END_TIME") if c in rows[0]
    ]
    return pd.DataFrame(rows)[cols]


def _from_sample() -> pd.DataFrame:
    logger.warning("Falling back to committed sample data: {}", config.SAMPLE_RATES_CSV)
    df = pd.read_csv(config.SAMPLE_RATES_CSV)
    df.columns = ["date", "rate_pct"]
    return df


def extract(offline: bool = False) -> pd.DataFrame:
    """Return a cleaned rate history and write it to RATES_RAW_CSV."""
    config.ensure_dirs()

    if offline or not config.ECOS_API_KEY:
        if not offline:
            logger.warning("No ECOS_API_KEY set; using sample data.")
        df = _from_sample()
    else:
        try:
            df = _from_ecos(config.ECOS_API_KEY)
        except Exception as exc:  # network/parse/auth errors -> deterministic fallback
            logger.warning("Live ECOS fetch failed ({}); using sample data.", exc)
            df = _from_sample()

    # --- clean ---
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["rate_pct"] = pd.to_numeric(df["rate_pct"], errors="coerce")
    df = df.dropna(subset=["date", "rate_pct"]).sort_values("date").reset_index(drop=True)

    # Quality gate: fail fast on bad source data before it flows downstream.
    validate_rates(df)

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
