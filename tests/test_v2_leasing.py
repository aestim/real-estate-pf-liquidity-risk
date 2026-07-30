from dataclasses import replace

import pytest

from pf_liquidity_risk.modeling.v2 import (
    OperatingLedgerConfig,
    build_base_operating_config,
    build_operating_ledger,
    validate_operating_ledger,
)


@pytest.fixture
def config() -> OperatingLedgerConfig:
    return build_base_operating_config()


def test_month_25_applies_anchor_rent_free_and_starts_other_lease_up(config):
    ledger = build_operating_ledger(config).ledger
    opening = ledger.loc[ledger["month"] == 25].iloc[0]

    assert opening["anchor_occupancy"] == pytest.approx(1.0)
    assert opening["non_anchor_occupancy"] == pytest.approx(0.20)
    assert opening["anchor_billed_rent"] == pytest.approx(0.0)
    assert opening["anchor_rent_free_concession"] == pytest.approx(opening["anchor_occupied_rent"])
    assert opening["property_noi"] < 0


def test_anchor_rent_begins_after_two_free_months(config):
    ledger = build_operating_ledger(config).ledger
    month_26 = ledger.loc[ledger["month"] == 26].iloc[0]
    month_27 = ledger.loc[ledger["month"] == 27].iloc[0]

    assert month_26["anchor_billed_rent"] == pytest.approx(0.0)
    assert month_27["anchor_billed_rent"] == pytest.approx(month_27["anchor_occupied_rent"])
    assert month_27["anchor_rent_free_concession"] == pytest.approx(0.0)


def test_non_anchor_reaches_and_holds_stabilized_occupancy(config):
    ledger = build_operating_ledger(config).ledger
    month_36 = ledger.loc[ledger["month"] == 36].iloc[0]
    month_60 = ledger.loc[ledger["month"] == 60].iloc[0]

    assert month_36["non_anchor_occupancy"] == pytest.approx(0.95)
    assert month_60["non_anchor_occupancy"] == pytest.approx(0.95)


def test_rent_growth_starts_after_first_operating_year(config):
    ledger = build_operating_ledger(config).ledger
    month_36 = ledger.loc[ledger["month"] == 36].iloc[0]
    month_37 = ledger.loc[ledger["month"] == 37].iloc[0]

    assert month_36["rent_multiplier"] == pytest.approx(1.0)
    assert month_37["rent_multiplier"] == pytest.approx(1.02)
    assert month_37["anchor_gross_potential_rent"] == pytest.approx(
        month_36["anchor_gross_potential_rent"] * 1.02
    )


def test_revenue_expense_and_noi_reconcile(config):
    result = build_operating_ledger(config)
    ledger = result.ledger

    assert (ledger["occupied_rent"] - ledger["rent_free_concession"]).to_numpy() == pytest.approx(
        ledger["billed_rent"].to_numpy()
    )
    assert (ledger["billed_rent"] - ledger["collection_loss"]).to_numpy() == pytest.approx(
        ledger["collected_rent"].to_numpy()
    )
    assert (ledger["collected_rent"] + ledger["other_income"]).to_numpy() == pytest.approx(
        ledger["effective_property_revenue"].to_numpy()
    )
    assert (
        ledger["effective_property_revenue"] - ledger["property_operating_expense"]
    ).to_numpy() == pytest.approx(ledger["property_noi"].to_numpy())

    validate_operating_ledger(result, config)


def test_underwriting_uses_trailing_three_month_average(config):
    result = build_operating_ledger(config)
    ledger = result.ledger
    expected = ledger.loc[ledger["month"].between(34, 36), "property_noi"].mean()

    assert result.underwritten_monthly_noi == pytest.approx(expected)
    assert result.underwritten_annual_noi == pytest.approx(expected * 12)
    assert result.first_positive_noi_month == 26


def test_month_36_bottom_up_noi_matches_contract_fixture(config):
    ledger = build_operating_ledger(config).ledger
    month_36 = ledger.loc[ledger["month"] == 36].iloc[0]

    assert month_36["gross_potential_rent"] == pytest.approx(9.6)
    assert month_36["occupied_rent"] == pytest.approx(9.3)
    assert month_36["property_noi"] == pytest.approx(6.252912)
    assert month_36["annualized_property_noi"] == pytest.approx(75.034944)


def test_config_rejects_occupancy_above_one(config):
    with pytest.raises(ValueError, match="between zero and one"):
        replace(config.anchor, stabilized_occupancy=1.1)
