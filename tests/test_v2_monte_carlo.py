import pandas as pd
import pytest

from pf_liquidity_risk.modeling.v2.monte_carlo import (
    REGIMES,
    ScenarioDraw,
    build_scenario_config,
    run_v2_monte_carlo,
    smooth_cost_weights,
    summarize_v2_results,
)
from pf_liquidity_risk.modeling.v2.project import run_project


def test_regime_probabilities_and_cost_weights_are_well_formed():
    assert sum(regime.probability for regime in REGIMES) == pytest.approx(1.0)
    weights = smooth_cost_weights(21)
    assert len(weights) == 21
    assert sum(weights) == pytest.approx(1.0)
    assert all(weight > 0 for weight in weights)


def test_scenario_config_keeps_budget_balanced_and_timelines_aligned():
    draw = ScenarioDraw(
        regime="stress",
        hard_cost_overrun=0.08,
        delay_months=3,
        rent_factor=0.90,
        stabilized_occupancy=0.85,
        lease_up_months=18,
        collection_loss_rate=0.03,
        interest_rate_shock=0.015,
        cap_rate_shock=0.008,
        maximum_ltv=0.60,
    )

    config = build_scenario_config(draw)

    assert config.development.uses.total == pytest.approx(
        config.development.sources.final_development_total
    )
    assert config.development.timeline.completion_month == 27
    assert config.operating.operations_start_month == 28
    assert config.operating.underwriting_month == 39
    assert config.operating.operations_end_month == 63
    assert config.operating.non_anchor.lease_up_months == 18


def test_operating_default_capitalizes_unpaid_claim_before_sale():
    draw = ScenarioDraw(
        regime="stress",
        hard_cost_overrun=0.08,
        delay_months=3,
        rent_factor=0.90,
        stabilized_occupancy=0.85,
        lease_up_months=18,
        collection_loss_rate=0.03,
        interest_rate_shock=0.015,
        cap_rate_shock=0.008,
        maximum_ltv=0.60,
    )

    result = run_project(build_scenario_config(draw))

    assert result.status == "operating_default_sale"
    assert result.ledger["capitalized_default_claim"].sum() > 0
    assert result.lender_shortfall > 0


def test_v2_monte_carlo_is_reproducible():
    first = run_v2_monte_carlo(iterations=40, seed=7)
    second = run_v2_monte_carlo(iterations=40, seed=7)

    pd.testing.assert_frame_equal(first, second)


def test_v2_monte_carlo_outputs_bounded_metrics():
    results = run_v2_monte_carlo(iterations=80, seed=42)
    summary = summarize_v2_results(results)

    assert len(results) == 80
    assert set(results["regime"]).issubset({"normal", "stress", "severe"})
    assert results["scenario_id"].is_unique
    assert (results["sponsor_equity_invested"] >= 50).all()
    assert (results["sponsor_distribution"] >= 0).all()
    assert (results["refi_funding_gap"] >= 0).all()
    assert (results["lender_shortfall"] >= 0).all()
    for value in summary.values():
        assert pd.notna(value)
    for key in (
        "refi_success_rate",
        "extension_rate",
        "distressed_or_default_rate",
        "successful_exit_rate",
        "mean_sponsor_loss_pct",
        "portfolio_sponsor_loss_pct",
    ):
        assert 0 <= summary[key] <= 1
