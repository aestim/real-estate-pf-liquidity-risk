from dataclasses import replace

import pytest

from pf_liquidity_risk.modeling.v2.project import (
    ProjectV2Config,
    build_base_project_config,
    run_project,
    validate_project_ledger,
)


def test_base_project_refinances_and_exits():
    result = run_project()

    assert result.status == "exit"
    assert result.terminal_month == 60
    assert len(result.refinance_attempts) == 1
    assert result.refinance_attempts[0].status == "refi_success"
    assert result.sale is not None
    assert not result.sale.distressed
    assert result.lender_shortfall == 0
    assert result.sponsor_distribution > 0
    assert result.preferred_distribution > 100
    assert result.sponsor_irr > 0
    assert result.combined_equity_irr > 0
    validate_project_ledger(result)


def test_base_project_uses_monthly_equity_cash_flow_timing():
    result = run_project()
    ledger = result.ledger

    assert ledger.loc[ledger["month"] == 0, "sponsor_equity_cash_flow"].iloc[0] == -50
    assert ledger.loc[ledger["month"] == 6, "preferred_equity_cash_flow"].iloc[0] == -100
    assert ledger.iloc[-1]["sponsor_equity_cash_flow"] > 0
    assert result.sponsor_equity_invested >= 50
    assert result.preferred_equity_invested == pytest.approx(100)


def test_tight_takeout_cap_uses_extension_then_distressed_sale():
    config = build_base_project_config()
    constrained_takeout = replace(config.takeout, lender_commitment_cap=400.0)
    constrained = replace(config, takeout=constrained_takeout)

    result = run_project(constrained)

    assert len(result.refinance_attempts) == 2
    assert all(attempt.status == "refi_shortfall" for attempt in result.refinance_attempts)
    assert result.status == "distressed_sale"
    assert result.terminal_month == 42
    assert result.sale is not None
    assert result.sale.distressed
    assert result.refi_funding_gap > 0


def test_equity_cure_can_complete_takeout_closing():
    config = build_base_project_config()
    base_result = run_project(config)
    base_decision = base_result.refinance_attempts[0]
    reduced_cap = base_decision.required_gross_draw - 10.0
    constrained_takeout = replace(config.takeout, lender_commitment_cap=reduced_cap)
    constrained = replace(config, takeout=constrained_takeout)

    result = run_project(constrained)

    assert result.refinance_attempts[0].status == "refi_success_with_cure"
    assert result.refinance_attempts[0].sponsor_equity_cure > 0
    assert result.status == "exit"
    assert result.sponsor_equity_invested > 50


def test_project_config_requires_aligned_operating_start():
    config = build_base_project_config()
    bad_operating = replace(config.operating, operations_start_month=26)

    with pytest.raises(ValueError, match="one month after completion"):
        ProjectV2Config(
            development=config.development,
            operating=bad_operating,
            takeout=config.takeout,
            sale=config.sale,
            resolution=config.resolution,
        )
