"""
SIMULATE stage: run the Monte Carlo engine with calibrated parameters and
persist per-scenario results to Parquet (the columnar landing format the
warehouse loads from).

Each run gets a batch_id + run timestamp so the warehouse can hold the history
of every simulation run, not just the latest.

Output: data/processed/simulation_results.parquet
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import uuid

from loguru import logger
import pandas as pd

from pf_liquidity_risk.configs import public_config
from pf_liquidity_risk.modeling.train import run_simulation
from pipeline import config


def simulate(iterations: int = 30000, seed: int = 42) -> pd.DataFrame:
    config.ensure_dirs()

    cfg = public_config.get_config()

    # Inject calibrated rates if the calibrate stage has run.
    if config.CALIBRATION_JSON.exists():
        params = json.loads(config.CALIBRATION_JSON.read_text())
        cfg.pre_refi_rate = tuple(params["pre_refi_rate"])
        cfg.post_refi_rate = tuple(params["post_refi_rate"])
        logger.info("Using calibrated rates pre={} post={}", cfg.pre_refi_rate, cfg.post_refi_rate)
    else:
        logger.warning("No calibration file; using default config rates.")

    df, cfg = run_simulation(iterations=iterations, seed=seed, config=cfg)

    # Tag every row with batch + config metadata (denormalized landing table).
    batch_id = uuid.uuid4().hex[:12]
    df = df.reset_index(drop=True)
    df.insert(0, "scenario_id", df.index.astype("int64"))
    df.insert(0, "batch_id", batch_id)
    df["run_ts"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    df["iterations"] = iterations
    df["seed"] = seed
    df["config_type"] = cfg.config_type
    df["cap_rate"] = cfg.cap_rate
    df["pre_refi_min"], df["pre_refi_mode"], df["pre_refi_max"] = cfg.pre_refi_rate
    df["post_refi_min"], df["post_refi_mode"], df["post_refi_max"] = cfg.post_refi_rate

    # Ensure optional columns exist (default/refi_fail rows omit some keys).
    for col in ("exit_multiple", "principal_at_refi", "refi_loan_amount"):
        if col not in df.columns:
            df[col] = pd.NA

    df.to_parquet(config.SIM_PARQUET, index=False)
    logger.success("Wrote {} scenarios (batch {}) -> {}", len(df), batch_id, config.SIM_PARQUET)
    return df


if __name__ == "__main__":
    simulate()
