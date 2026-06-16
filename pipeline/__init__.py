"""
Data-engineering pipeline for the PF liquidity-risk model.

Stages (see pipeline.cli):
    extract  -> pull interest-rate history (real source, with offline fallback)
    calibrate-> turn rate history into triangular model parameters
    simulate -> run the Monte Carlo engine, write results to Parquet
    load     -> load Parquet into a DuckDB star schema (fact + dims)
    transform-> run SQL marts against DuckDB, export analytics tables

Run the whole thing with:  python -m pipeline.cli run
"""

__all__ = ["config"]
