"""
TRANSFORM stage: run the SQL marts against the DuckDB warehouse and export the
results to CSV in reports/ for downstream consumers (BI tools, the README, etc.).

Outputs: mart tables inside DuckDB + reports/<mart>.csv
"""

from __future__ import annotations

import duckdb
from loguru import logger

from pipeline import config

MARTS = [
    "mart_outcome_summary.sql",
    "mart_irr_percentiles.sql",
    "mart_survival_curve.sql",
]


def transform() -> dict[str, int]:
    if not config.DUCKDB_PATH.exists():
        raise FileNotFoundError(f"Run the load stage first: {config.DUCKDB_PATH} missing")

    con = duckdb.connect(str(config.DUCKDB_PATH))
    counts: dict[str, int] = {}
    try:
        for mart_file in MARTS:
            con.execute((config.SQL_DIR / mart_file).read_text())
            table = mart_file.replace(".sql", "")
            df = con.execute(f"SELECT * FROM {table}").df()
            out = config.REPORTS_DIR / f"{table}.csv"
            df.to_csv(out, index=False)
            counts[table] = len(df)
            logger.success("Built {} ({} rows) -> {}", table, len(df), out)
    finally:
        con.close()
    return counts


if __name__ == "__main__":
    transform()
