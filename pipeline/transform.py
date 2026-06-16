"""
TRANSFORM stage: run the dbt (dbt-duckdb) project against the warehouse.

dbt owns all modeling and data tests: raw_scenarios -> staging -> dims/fact ->
marts, with not_null / unique / accepted_values / relationships / range tests.
After a successful build, the mart tables are exported to reports/ as CSV for
downstream/BI consumption.

Outputs: mart tables inside DuckDB + reports/<mart>.csv
"""

from __future__ import annotations

import os

from dbt.cli.main import dbtRunner
import duckdb
from loguru import logger

from pipeline import config

MARTS = ["mart_outcome_summary", "mart_irr_percentiles", "mart_survival_curve"]


def transform() -> dict[str, int]:
    if not config.DUCKDB_PATH.exists():
        raise FileNotFoundError(f"Run the load stage first: {config.DUCKDB_PATH} missing")

    # Point dbt at our warehouse via an absolute path (profiles.yml reads this).
    os.environ["PF_DUCKDB_PATH"] = str(config.DUCKDB_PATH.resolve())

    logger.info("Running dbt build (models + data tests)...")
    result = dbtRunner().invoke(
        [
            "build",
            "--project-dir",
            str(config.DBT_DIR),
            "--profiles-dir",
            str(config.DBT_DIR),
        ]
    )
    if not result.success:
        raise RuntimeError("dbt build failed (see dbt output above)")

    # Export mart tables to CSV for BI / README consumption.
    counts: dict[str, int] = {}
    # Note: open with default (read-write) config — dbt-duckdb may still hold an
    # in-process connection, and a read_only connection would conflict with it.
    con = duckdb.connect(str(config.DUCKDB_PATH))
    try:
        for mart in MARTS:
            df = con.execute(f"SELECT * FROM {mart}").df()
            out = config.REPORTS_DIR / f"{mart}.csv"
            df.to_csv(out, index=False)
            counts[mart] = len(df)
            logger.success("Exported {} ({} rows) -> {}", mart, len(df), out)
    finally:
        con.close()
    return counts


if __name__ == "__main__":
    transform()
