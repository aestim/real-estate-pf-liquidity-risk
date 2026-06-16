"""Central paths and constants for the pipeline (single source of truth)."""

from __future__ import annotations

from pathlib import Path

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

# Rate source. FRED's CSV endpoint needs no API key.
# DGS10 = 10-Year Treasury; used here only as an illustrative macro rate anchor.
FRED_SERIES_ID = "DGS10"
FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"

# PF spread (basis points) added on top of the macro anchor to approximate
# construction-phase PF lending rates. Illustrative, documented assumption.
PF_SPREAD_PRE_REFI = 0.06  # +600bps over anchor during construction
PF_SPREAD_POST_REFI = -0.02  # -200bps after refinancing to a facility loan


def ensure_dirs() -> None:
    for d in (RAW_DIR, PROCESSED_DIR, REPORTS_DIR):
        d.mkdir(parents=True, exist_ok=True)
