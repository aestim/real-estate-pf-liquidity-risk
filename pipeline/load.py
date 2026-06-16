"""
LOAD stage: land the Parquet file into DuckDB as the raw table `raw_scenarios`.

This stage only lands raw data (EL of "ELT"); all modeling — staging, dims,
fact, marts — is owned by dbt (the T), so there is a single source of truth for
transforms. Run `transform` (or `dbt build`) after this.

Output: data/processed/pf_warehouse.duckdb  (table: raw_scenarios)
"""

from __future__ import annotations

import duckdb
from loguru import logger

from pipeline import config


def load() -> None:
    config.ensure_dirs()
    if not config.SIM_PARQUET.exists():
        raise FileNotFoundError(f"Run the simulate stage first: {config.SIM_PARQUET} missing")

    con = duckdb.connect(str(config.DUCKDB_PATH))
    try:
        # Register the Parquet as a raw landing table (idempotent rebuild).
        con.execute(
            "CREATE OR REPLACE TABLE raw_scenarios AS SELECT * FROM read_parquet(?)",
            [str(config.SIM_PARQUET)],
        )
        rows = con.execute("SELECT COUNT(*) FROM raw_scenarios").fetchone()[0]
        logger.success("Landed {} rows -> raw_scenarios in {}", rows, config.DUCKDB_PATH)
    finally:
        con.close()


if __name__ == "__main__":
    load()
