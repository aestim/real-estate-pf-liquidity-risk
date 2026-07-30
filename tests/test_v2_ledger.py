from dataclasses import replace

import pytest

from pf_liquidity_risk.modeling.v2 import (
    DevelopmentLedgerConfig,
    build_base_case_config,
    build_development_ledger,
    validate_ledger,
)


@pytest.fixture
def config() -> DevelopmentLedgerConfig:
    return build_base_case_config()


def test_budgeted_sources_and_uses_balance(config):
    assert config.uses.total == pytest.approx(1000.0)
    assert config.sources.final_development_total == pytest.approx(1000.0)


def test_month_zero_equity_and_bridge_fund_land(config):
    result = build_development_ledger(config)
    month_zero = result.ledger.iloc[0]

    assert month_zero["sponsor_equity_draw"] == pytest.approx(50.0)
    assert month_zero["bridge_loan_draw"] == pytest.approx(250.0)
    assert month_zero["land_cost"] == pytest.approx(300.0)
    assert month_zero["closing_cash"] == pytest.approx(0.0)


def test_main_pf_draw_replaces_temporary_bridge(config):
    result = build_development_ledger(config)
    close = result.ledger.loc[result.ledger["month"] == config.timeline.main_pf_close_month].iloc[
        0
    ]

    assert close["bridge_repayment"] == pytest.approx(close["bridge_opening_balance"])
    assert close["senior_pf_draw"] == pytest.approx(close["bridge_repayment"])
    assert close["bridge_closing_balance"] == pytest.approx(0.0)


def test_cost_schedules_use_full_land_hard_and_soft_budgets(config):
    ledger = build_development_ledger(config).ledger

    assert ledger["land_cost"].sum() == pytest.approx(config.uses.land_and_acquisition)
    assert ledger["hard_cost"].sum() == pytest.approx(config.uses.hard_cost)
    assert ledger["soft_cost"].sum() == pytest.approx(config.uses.soft_cost)


def test_monthly_cash_and_debt_balances_reconcile(config):
    result = build_development_ledger(config)
    ledger = result.ledger

    assert (
        ledger["opening_cash"] + ledger["total_sources"] - ledger["total_uses"]
    ).to_numpy() == pytest.approx(ledger["closing_cash"].to_numpy())
    assert (
        ledger["bridge_opening_balance"] + ledger["bridge_loan_draw"] - ledger["bridge_repayment"]
    ).to_numpy() == pytest.approx(ledger["bridge_closing_balance"].to_numpy())
    assert (
        ledger["senior_opening_balance"] + ledger["senior_pf_draw"]
    ).to_numpy() == pytest.approx(ledger["senior_closing_balance"].to_numpy())
    assert (
        ledger["subordinate_opening_balance"] + ledger["subordinate_loan_draw"]
    ).to_numpy() == pytest.approx(ledger["subordinate_closing_balance"].to_numpy())

    validate_ledger(result, config)


def test_base_case_completes_within_every_commitment(config):
    result = build_development_ledger(config)
    ledger = result.ledger

    assert result.status == "completed"
    assert result.default_month is None
    assert ledger["month"].tolist() == list(range(config.timeline.completion_month + 1))
    assert ledger["closing_cash"].min() >= 0
    assert ledger["bridge_loan_draw"].sum() <= config.sources.bridge_commitment
    assert ledger["senior_pf_draw"].sum() <= config.sources.senior_pf_commitment
    assert ledger["subordinate_loan_draw"].sum() <= config.sources.subordinate_loan_commitment
    assert result.undrawn_senior_commitment > 0


def test_bridge_capacity_shortfall_becomes_explicit_funding_default(config):
    constrained_sources = replace(config.sources, bridge_commitment=255.0)
    constrained = replace(config, sources=constrained_sources)

    result = build_development_ledger(constrained)

    assert result.status == "funding_default"
    assert result.default_month is not None
    assert result.ledger.iloc[-1]["funding_gap"] > 0
    assert result.ledger.iloc[-1]["closing_cash"] < 0


def test_base_case_financing_cost_fits_budget_and_contingency(config):
    result = build_development_ledger(config)
    financing_cost = result.ledger["financing_cost"].sum()

    assert financing_cost <= (
        config.uses.financing_cost_and_interest_reserve + config.uses.contingency
    )
    assert result.development_cost_total <= config.uses.total
    assert result.unspent_development_budget >= 0
