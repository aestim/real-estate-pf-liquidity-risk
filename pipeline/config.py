"""Central paths and constants for the pipeline (single source of truth)."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load secrets (e.g. ECOS_API_KEY) from a local .env file if present.
# .env is gitignored, so keys never get committed.
load_dotenv()

# Repo-relative paths (this file lives in <repo>/pipeline/config.py)
REPO_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = REPO_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
REPORTS_DIR = REPO_ROOT / "reports"
SQL_DIR = Path(__file__).resolve().parent / "sql"

# Artifacts
RATES_RAW_CSV = RAW_DIR / "interest_rates.csv"  # extract output
SAMPLE_RATES_CSV = RAW_DIR / "sample_interest_rates.csv"  # committed offline fallback
CALIBRATION_JSON = PROCESSED_DIR / "calibrated_params.json"  # calibrate output
SIM_PARQUET = PROCESSED_DIR / "simulation_results.parquet"  # simulate output
DUCKDB_PATH = PROCESSED_DIR / "pf_warehouse.duckdb"  # load target

# Rate source: Bank of Korea ECOS (한국은행 경제통계시스템).
# Anchor = CD 91-day yield (단기 시장조달금리), the closest public proxy for
# Korean PF / bridge-loan funding cost. Live fetch needs a free ECOS API key
# (env ECOS_API_KEY); without it the pipeline falls back to committed sample data.
RATE_SOURCE_NAME = "BOK ECOS — CD(91-day)"
ECOS_API_KEY = os.environ.get("ECOS_API_KEY", "")
ECOS_STAT_CODE = "722Y001"  # 시장금리 (market interest rates) table
ECOS_ITEM_CODE = "010502000"  # CD(91일)
ECOS_CYCLE = "M"  # monthly
ECOS_START = "202001"
ECOS_END = "203012"
ECOS_URL = (
    "https://ecos.bok.or.kr/api/StatisticSearch/{key}/json/kr/1/1000/"
    "{stat}/{cycle}/{start}/{end}/{item}"
)

# PF spread added on top of the CD anchor to approximate Korean PF lending rates.
# Illustrative, documented assumption (bridge/construction loans price well above CD).
PF_SPREAD_PRE_REFI = 0.06  # +600bps over CD during construction (high-rate bridge phase)
PF_SPREAD_POST_REFI = -0.02  # -200bps after refinancing to a stabilized facility loan


def ensure_dirs() -> None:
    for d in (RAW_DIR, PROCESSED_DIR, REPORTS_DIR):
        d.mkdir(parents=True, exist_ok=True)
