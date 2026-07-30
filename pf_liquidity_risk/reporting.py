"""Pure reporting calculations shared by the dashboard and tests."""

from __future__ import annotations

import numpy as np
import pandas as pd


def equity_loss_metrics(df: pd.DataFrame, initial_equity: float) -> dict[str, object]:
    """Calculate equity-loss metrics against the equity basis of the saved run."""
    if initial_equity <= 0:
        raise ValueError("initial_equity must be positive")
    if "final_equity" not in df:
        raise ValueError("simulation results must contain final_equity")
    if df.empty:
        raise ValueError("simulation results cannot be empty")

    loss = initial_equity - df["final_equity"]
    return {
        "loss": loss,
        "var_90_pct": float(np.percentile(loss, 90) / initial_equity * 100),
        "var_95_pct": float(np.percentile(loss, 95) / initial_equity * 100),
        "var_99_pct": float(np.percentile(loss, 99) / initial_equity * 100),
        "expected_loss_pct": float(loss.mean() / initial_equity * 100),
    }
