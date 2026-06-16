"""
LOAD stage: load the Parquet landing file into a DuckDB warehouse and build a
star schema (fact_scenario + dim_batch + dim_outcome) via schema.sql.

Output: data/processed/pf_warehouse.duckdb
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
        con.execute((config.SQL_DIR / "schema.sql").read_text())

        rows = con.execute("SELECT COUNT(*) FROM fact_scenario").fetchone()[0]
        batches = con.execute("SELECT COUNT(*) FROM dim_batch").fetchone()[0]
        logger.success(
            "Loaded {} fact rows across {} batch(es) -> {}", rows, batches, config.DUCKDB_PATH
        )
    finally:
        con.close()


if __name__ == "__main__":
    load()
