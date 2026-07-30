from dataclasses import replace

import pytest

from pf_liquidity_risk.modeling.v2.refinance import (
    TakeoutTerms,
    fund_refinance,
    size_takeout,
)


def test_contract_fixture_is_ltv_constrained():
    terms = TakeoutTerms()

    capacity = size_takeout(75.0, terms)

    assert capacity.property_value == pytest.approx(1363.6363636)
    assert capacity.ltv_capacity == pytest.approx(886.3636364)
    assert capacity.debt_yield_capacity == pytest.approx(937.5)
    assert capacity.dscr_capacity == pytest.approx(974.0259740)
    assert capacity.binding_constraint == "ltv"
    assert capacity.gross_capacity == pytest.approx(capacity.ltv_capacity)


def test_successful_closing_draws_only_required_takeout_amount():
    terms = TakeoutTerms()
    capacity = size_takeout(75.0, terms)

    decision = fund_refinance(
        capacity=capacity,
        debt_payoff_requirement=860.0,
        available_project_cash=0.0,
        sponsor_equity_cure_commitment=0.0,
        terms=terms,
    )

    assert decision.status == "refi_success"
    assert decision.required_gross_draw == pytest.approx(860 / 0.99)
    assert decision.gross_takeout_draw < capacity.gross_capacity
    assert decision.net_takeout_proceeds == pytest.approx(860.0)
    assert decision.funding_gap == 0


def test_project_cash_reduces_required_takeout_draw():
    terms = TakeoutTerms()
    capacity = size_takeout(75.0, terms)

    no_cash = fund_refinance(
        capacity=capacity,
        debt_payoff_requirement=800.0,
        available_project_cash=0.0,
        sponsor_equity_cure_commitment=0.0,
        terms=terms,
    )
    with_cash = fund_refinance(
        capacity=capacity,
        debt_payoff_requirement=800.0,
        available_project_cash=20.0,
        sponsor_equity_cure_commitment=0.0,
        terms=terms,
    )

    assert with_cash.gross_takeout_draw < no_cash.gross_takeout_draw
    assert with_cash.project_cash_applied == pytest.approx(20.0)


def test_equity_cure_is_funded_only_when_it_completes_closing():
    terms = TakeoutTerms()
    constrained = replace(terms, lender_commitment_cap=790.0)
    capacity = size_takeout(75.0, constrained)

    success = fund_refinance(
        capacity=capacity,
        debt_payoff_requirement=800.0,
        available_project_cash=0.0,
        sponsor_equity_cure_commitment=20.0,
        terms=constrained,
    )
    failure = fund_refinance(
        capacity=capacity,
        debt_payoff_requirement=850.0,
        available_project_cash=0.0,
        sponsor_equity_cure_commitment=20.0,
        terms=constrained,
    )

    assert success.status == "refi_success_with_cure"
    assert 0 < success.sponsor_equity_cure <= 20
    assert failure.status == "refi_shortfall"
    assert failure.sponsor_equity_cure == 0
    assert failure.gross_takeout_draw == 0
    assert failure.funding_gap > 0


def test_non_positive_noi_has_zero_income_based_capacity():
    capacity = size_takeout(0.0)

    assert capacity.property_value == 0
    assert capacity.gross_capacity == 0
