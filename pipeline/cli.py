"""
Pipeline orchestration CLI.

Examples:
    python -m pipeline.cli run                 # full pipeline end-to-end
    python -m pipeline.cli run --offline       # use committed sample rate data
    python -m pipeline.cli extract --offline   # single stage
    python -m pipeline.cli simulate --iterations 5000
    python -m pipeline.cli query "SELECT * FROM mart_outcome_summary"
"""

from __future__ import annotations

import duckdb
from loguru import logger
import typer

from pipeline import calibrate as calibrate_stage
from pipeline import config, extract_rates
from pipeline import load as load_stage
from pipeline import simulate as simulate_stage
from pipeline import transform as transform_stage

app = typer.Typer(add_completion=False, help="PF liquidity-risk data pipeline.")


@app.command()
def extract(
    offline: bool = typer.Option(False, help="Use committed sample data instead of the network."),
):
    """EXTRACT: pull interest-rate history."""
    extract_rates.extract(offline=offline)


@app.command()
def calibrate():
    """CALIBRATE: derive triangular model parameters from rate history."""
    calibrate_stage.calibrate()


@app.command("ecos-items")
def ecos_items(stat: str = config.ECOS_STAT_CODE):
    """List ECOS item codes for a stat table (to confirm the right rate series)."""
    df = extract_rates.list_items(stat)
    print(df.to_string(index=False))


@app.command()
def simulate(iterations: int = 30000, seed: int = 42):
    """SIMULATE: run Monte Carlo, write Parquet."""
    simulate_stage.simulate(iterations=iterations, seed=seed)


@app.command()
def load():
    """LOAD: build the DuckDB star schema from Parquet."""
    load_stage.load()


@app.command()
def transform():
    """TRANSFORM: run SQL marts, export CSVs to reports/."""
    transform_stage.transform()


@app.command()
def run(
    iterations: int = 30000,
    seed: int = 42,
    offline: bool = typer.Option(False, help="Use committed sample rate data."),
):
    """Run the full pipeline: extract -> calibrate -> simulate -> load -> transform."""
    logger.info("=== PF liquidity-risk pipeline: full run ===")
    rates = extract_rates.extract(offline=offline)
    calibrate_stage.calibrate(rates)
    simulate_stage.simulate(iterations=iterations, seed=seed)
    load_stage.load()
    counts = transform_stage.transform()
    logger.success("Pipeline complete. Marts: {}", counts)


@app.command()
def query(sql: str):
    """Run an ad-hoc SQL query against the warehouse."""
    con = duckdb.connect(str(config.DUCKDB_PATH), read_only=True)
    try:
        print(con.execute(sql).df().to_string(index=False))
    finally:
        con.close()


if __name__ == "__main__":
    app()
