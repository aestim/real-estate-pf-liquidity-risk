import pytest

from pf_liquidity_risk.modeling.v2.returns import (
    periodic_irr,
    realized_equity_multiple,
)
from pf_liquidity_risk.modeling.v2.waterfall import run_sale_waterfall


def test_periodic_irr_uses_monthly_cash_flow_timing():
    cash_flows = [-100.0] + [0.0] * 11 + [110.0]

    assert periodic_irr(cash_flows) == pytest.approx(0.10, abs=1e-8)
    assert realized_equity_multiple(cash_flows) == pytest.approx(1.10)


def test_periodic_irr_returns_none_without_a_sign_change():
    assert periodic_irr([-100.0, -10.0, 0.0]) is None
    assert periodic_irr([0.0, 10.0]) is None


def test_sale_waterfall_respects_debt_and_equity_priority():
    result = run_sale_waterfall(
        annualized_noi=75.0,
        sale_month=60,
        project_cash=10.0,
        senior_debt=0.0,
        subordinate_debt=0.0,
        takeout_debt=800.0,
        preferred_equity_principal=100.0,
        preferred_funding_month=6,
        distressed=False,
    )

    assert result.gross_sale_proceeds == pytest.approx(75 / 0.0575)
    assert result.takeout_debt_paid == pytest.approx(800.0)
    assert result.preferred_distribution == pytest.approx(result.preferred_claim)
    assert result.sponsor_distribution > 0
    assert result.lender_shortfall == 0


def test_distressed_sale_can_leave_lender_shortfall_and_zero_equity():
    result = run_sale_waterfall(
        annualized_noi=30.0,
        sale_month=42,
        project_cash=0.0,
        senior_debt=700.0,
        subordinate_debt=100.0,
        takeout_debt=0.0,
        preferred_equity_principal=100.0,
        preferred_funding_month=6,
        distressed=True,
    )

    assert result.lender_shortfall > 0
    assert result.preferred_distribution == 0
    assert result.sponsor_distribution == 0
