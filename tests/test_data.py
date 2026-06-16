"""
Tests for the PF liquidity-risk Monte Carlo engine.

These cover the simulation contract (valid outcomes, reproducibility) and the
core financial logic (interest capitalization, refinancing gate, insolvency).
"""

import numpy as np
import pytest

from pf_liquidity_risk.configs import public_config
from pf_liquidity_risk.modeling.config_model import PFConfig
from pf_liquidity_risk.modeling.train import PFInvestmentModel, run_simulation

VALID_STATUSES = {"exit", "default", "refi_fail", "survived_no_exit"}


@pytest.fixture
def cfg() -> PFConfig:
    return public_config.get_config()


def test_config_is_well_formed(cfg):
    assert cfg.initial_equity > 0
    assert cfg.senior_loan > 0
    assert 0 < cfg.cap_rate < 1
    assert cfg.completion_target_month < cfg.court_opening_month < cfg.exit_month
    # Triangular params must be ordered (min <= mode <= max)
    for lo, mode, hi in (cfg.pre_refi_rate, cfg.post_refi_rate,
                         cfg.stabilization_revenue_dist, cfg.post_court_revenue_dist,
                         cfg.target_refi_ltv_dist):
        assert lo <= mode <= hi


def test_single_path_returns_valid_status(cfg):
    np.random.seed(0)
    result = PFInvestmentModel(cfg).simulate_path()
    assert result["status"] in VALID_STATUSES
    assert 1 <= result["month"] <= cfg.exit_month
    assert result["final_equity"] >= 0


def test_simulation_is_reproducible(cfg):
    df1, _ = run_simulation(iterations=500, seed=123, config=cfg)
    df2, _ = run_simulation(iterations=500, seed=123, config=cfg)
    assert df1["status"].tolist() == df2["status"].tolist()


def test_outcome_probabilities_sum_to_one(cfg):
    df, _ = run_simulation(iterations=2000, seed=42, config=cfg)
    assert set(df["status"].unique()).issubset(VALID_STATUSES)
    assert np.isclose(df["status"].value_counts(normalize=True).sum(), 1.0)


def test_high_leverage_produces_refinancing_risk(cfg):
    """The whole thesis: this deal is dominated by refinancing failure."""
    df, _ = run_simulation(iterations=3000, seed=42, config=cfg)
    share = df["status"].value_counts(normalize=True)
    assert share.get("refi_fail", 0) > 0.5


def test_lower_leverage_improves_survival(cfg):
    """Sanity check on the model's economics: less debt -> fewer refi failures."""
    high_lev, _ = run_simulation(iterations=3000, seed=7, config=cfg)

    safer = public_config.get_config()
    safer.senior_loan = cfg.senior_loan * 0.4  # much less debt
    low_lev, _ = run_simulation(iterations=3000, seed=7, config=safer)

    high_fail = high_lev["status"].value_counts(normalize=True).get("refi_fail", 0)
    low_fail = low_lev["status"].value_counts(normalize=True).get("refi_fail", 0)
    assert low_fail < high_fail


def test_exit_cases_have_finite_irr(cfg):
    df, _ = run_simulation(iterations=3000, seed=42, config=cfg)
    exits = df[df["status"] == "exit"]
    if not exits.empty:
        assert exits["irr"].notna().all()
        assert np.isfinite(exits["irr"]).all()
