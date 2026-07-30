"""Monthly Sources & Uses ledger for the deterministic V2 base case."""

from dataclasses import dataclass
import math
from typing import Any

import pandas as pd

from pf_liquidity_risk.modeling.v2.config import (
    DevelopmentLedgerConfig,
    build_base_case_config,
)


class LedgerInvariantError(RuntimeError):
    """Raised when a generated ledger violates its accounting contract."""


@dataclass(frozen=True)
class DevelopmentLedgerResult:
    """A development ledger and its terminal funding status."""

    ledger: pd.DataFrame
    status: str
    default_month: int | None
    development_cost_total: float
    gross_sources_total: float
    gross_uses_total: float
    unspent_development_budget: float
    undrawn_senior_commitment: float


def _phase(month: int, config: DevelopmentLedgerConfig) -> str:
    timeline = config.timeline
    if month == timeline.land_acquisition_month:
        return "land_acquisition"
    if month < timeline.main_pf_close_month:
        return "predevelopment"
    if month == timeline.main_pf_close_month:
        return "main_pf_conversion"
    if month < timeline.completion_month:
        return "construction"
    return "completion"


def _scheduled_costs(month: int, config: DevelopmentLedgerConfig) -> tuple[float, float, float]:
    """Return land, hard, and soft costs for one month."""
    timeline = config.timeline
    uses = config.uses

    land_cost = uses.land_and_acquisition if month == timeline.land_acquisition_month else 0.0

    hard_cost = 0.0
    if month in timeline.construction_months:
        index = month - timeline.construction_start_month
        hard_cost = uses.hard_cost * config.hard_cost_weights[index]

    soft_cost = 0.0
    if month in timeline.predevelopment_months:
        soft_cost = config.predevelopment_soft_cost / len(timeline.predevelopment_months)
    elif month in timeline.construction_months:
        construction_soft_cost = uses.soft_cost - config.predevelopment_soft_cost
        soft_cost = construction_soft_cost / len(timeline.construction_months)

    return land_cost, hard_cost, soft_cost


def _cap_draw(required: float, remaining_commitment: float) -> float:
    return min(max(required, 0.0), max(remaining_commitment, 0.0))


def build_development_ledger(
    config: DevelopmentLedgerConfig | None = None,
) -> DevelopmentLedgerResult:
    """Build Months 0 through completion using explicit cash and debt movements.

    Interest is paid as a monthly cash use.  When loan proceeds fund that use,
    principal increases through the corresponding draw; interest is not added a
    second time directly to principal.
    """

    config = config or build_base_case_config()
    rows: list[dict[str, Any]] = []

    cash = 0.0
    bridge_balance = 0.0
    senior_balance = 0.0
    subordinate_balance = 0.0

    sponsor_common_drawn = 0.0
    sponsor_cure_drawn = 0.0
    preferred_drawn = 0.0
    bridge_drawn = 0.0
    senior_drawn = 0.0
    subordinate_drawn = 0.0

    status = "completed"
    default_month: int | None = None
    tolerance = config.amount_tolerance

    for month in range(config.timeline.completion_month + 1):
        opening_cash = cash
        bridge_opening = bridge_balance
        senior_opening = senior_balance
        subordinate_opening = subordinate_balance

        land_cost, hard_cost, soft_cost = _scheduled_costs(month, config)

        financing_fee = 0.0
        if month == 1:
            financing_fee += config.financing.bridge_upfront_fee
        if month == config.timeline.main_pf_close_month:
            financing_fee += config.financing.main_pf_upfront_fee

        bridge_interest = (
            bridge_opening * config.financing.bridge_annual_rate / 12
            if 1 <= month <= config.timeline.main_pf_close_month
            else 0.0
        )
        senior_interest = senior_opening * config.financing.senior_pf_annual_rate / 12
        subordinate_interest = subordinate_opening * config.financing.subordinate_annual_rate / 12
        bridge_repayment = bridge_opening if month == config.timeline.main_pf_close_month else 0.0

        financing_cost = financing_fee + bridge_interest + senior_interest + subordinate_interest
        development_cost_uses = land_cost + hard_cost + soft_cost + financing_cost
        total_uses = development_cost_uses + bridge_repayment

        sponsor_equity_draw = 0.0
        sponsor_cure_draw = 0.0
        preferred_equity_draw = 0.0
        bridge_loan_draw = 0.0
        subordinate_loan_draw = 0.0
        senior_pf_draw = 0.0

        if month == config.timeline.land_acquisition_month:
            sponsor_equity_draw = config.sources.sponsor_common_equity
            bridge_loan_draw = config.sources.bridge_initial_draw
        elif month < config.timeline.main_pf_close_month:
            cash_need = total_uses - opening_cash
            bridge_loan_draw = _cap_draw(
                cash_need,
                config.sources.bridge_commitment - bridge_drawn,
            )
        elif month == config.timeline.main_pf_close_month:
            preferred_equity_draw = config.sources.external_preferred_equity
            subordinate_loan_draw = config.sources.subordinate_loan_commitment
            # Preserve the transaction contract: the first senior draw takes
            # out the temporary bridge instead of treating both as permanent
            # development sources.
            senior_pf_draw = _cap_draw(
                bridge_repayment,
                config.sources.senior_pf_commitment - senior_drawn,
            )

        provisional_sources = (
            sponsor_equity_draw
            + preferred_equity_draw
            + bridge_loan_draw
            + subordinate_loan_draw
            + senior_pf_draw
        )
        remaining_need = total_uses - opening_cash - provisional_sources

        if month >= config.timeline.main_pf_close_month and remaining_need > tolerance:
            additional_senior_draw = _cap_draw(
                remaining_need,
                config.sources.senior_pf_commitment - senior_drawn - senior_pf_draw,
            )
            senior_pf_draw += additional_senior_draw
            provisional_sources += additional_senior_draw
            remaining_need -= additional_senior_draw

        if remaining_need > tolerance:
            sponsor_cure_draw = _cap_draw(
                remaining_need,
                config.sources.additional_sponsor_equity_commitment - sponsor_cure_drawn,
            )
            provisional_sources += sponsor_cure_draw

        total_sources = provisional_sources
        closing_cash = opening_cash + total_sources - total_uses
        if abs(closing_cash) <= tolerance:
            closing_cash = 0.0

        bridge_closing = bridge_opening + bridge_loan_draw - bridge_repayment
        senior_closing = senior_opening + senior_pf_draw
        subordinate_closing = subordinate_opening + subordinate_loan_draw

        sponsor_common_drawn += sponsor_equity_draw
        sponsor_cure_drawn += sponsor_cure_draw
        preferred_drawn += preferred_equity_draw
        bridge_drawn += bridge_loan_draw
        senior_drawn += senior_pf_draw
        subordinate_drawn += subordinate_loan_draw

        rows.append(
            {
                "month": month,
                "phase": _phase(month, config),
                "opening_cash": opening_cash,
                "sponsor_equity_draw": sponsor_equity_draw,
                "sponsor_cure_draw": sponsor_cure_draw,
                "preferred_equity_draw": preferred_equity_draw,
                "bridge_loan_draw": bridge_loan_draw,
                "subordinate_loan_draw": subordinate_loan_draw,
                "senior_pf_draw": senior_pf_draw,
                "total_sources": total_sources,
                "land_cost": land_cost,
                "hard_cost": hard_cost,
                "soft_cost": soft_cost,
                "financing_fee": financing_fee,
                "bridge_interest": bridge_interest,
                "senior_interest": senior_interest,
                "subordinate_interest": subordinate_interest,
                "financing_cost": financing_cost,
                "development_cost_uses": development_cost_uses,
                "bridge_repayment": bridge_repayment,
                "total_uses": total_uses,
                "closing_cash": closing_cash,
                "bridge_opening_balance": bridge_opening,
                "bridge_closing_balance": bridge_closing,
                "senior_opening_balance": senior_opening,
                "senior_closing_balance": senior_closing,
                "subordinate_opening_balance": subordinate_opening,
                "subordinate_closing_balance": subordinate_closing,
                "cumulative_sponsor_common_draw": sponsor_common_drawn,
                "cumulative_sponsor_cure_draw": sponsor_cure_drawn,
                "cumulative_preferred_equity_draw": preferred_drawn,
                "cumulative_bridge_draw": bridge_drawn,
                "cumulative_subordinate_draw": subordinate_drawn,
                "cumulative_senior_draw": senior_drawn,
                "funding_gap": max(0.0, -closing_cash),
            }
        )

        cash = closing_cash
        bridge_balance = bridge_closing
        senior_balance = senior_closing
        subordinate_balance = subordinate_closing

        if closing_cash < -tolerance:
            status = "funding_default"
            default_month = month
            break

    ledger = pd.DataFrame(rows)
    result = DevelopmentLedgerResult(
        ledger=ledger,
        status=status,
        default_month=default_month,
        development_cost_total=float(ledger["development_cost_uses"].sum()),
        gross_sources_total=float(ledger["total_sources"].sum()),
        gross_uses_total=float(ledger["total_uses"].sum()),
        unspent_development_budget=(
            config.uses.total - float(ledger["development_cost_uses"].sum())
        ),
        undrawn_senior_commitment=(
            config.sources.senior_pf_commitment - float(ledger["senior_pf_draw"].sum())
        ),
    )
    validate_ledger(result, config)
    return result


def _assert_series_close(
    actual: pd.Series,
    expected: pd.Series,
    *,
    tolerance: float,
    label: str,
) -> None:
    differences = (actual - expected).abs()
    if bool((differences > tolerance).any()):
        month = int(actual.index[differences.argmax()])
        raise LedgerInvariantError(f"{label} does not reconcile at row {month}")


def validate_ledger(
    result: DevelopmentLedgerResult,
    config: DevelopmentLedgerConfig,
) -> None:
    """Validate cash, debt, budget, and commitment invariants."""

    ledger = result.ledger
    tolerance = config.amount_tolerance
    if ledger.empty:
        raise LedgerInvariantError("ledger cannot be empty")

    expected_cash = ledger["opening_cash"] + ledger["total_sources"] - ledger["total_uses"]
    _assert_series_close(
        ledger["closing_cash"],
        expected_cash,
        tolerance=tolerance,
        label="cash",
    )
    _assert_series_close(
        ledger["bridge_closing_balance"],
        (
            ledger["bridge_opening_balance"]
            + ledger["bridge_loan_draw"]
            - ledger["bridge_repayment"]
        ),
        tolerance=tolerance,
        label="bridge balance",
    )
    _assert_series_close(
        ledger["senior_closing_balance"],
        ledger["senior_opening_balance"] + ledger["senior_pf_draw"],
        tolerance=tolerance,
        label="senior balance",
    )
    _assert_series_close(
        ledger["subordinate_closing_balance"],
        ledger["subordinate_opening_balance"] + ledger["subordinate_loan_draw"],
        tolerance=tolerance,
        label="subordinate balance",
    )

    commitment_checks = {
        "bridge": (
            float(ledger["bridge_loan_draw"].sum()),
            config.sources.bridge_commitment,
        ),
        "senior": (
            float(ledger["senior_pf_draw"].sum()),
            config.sources.senior_pf_commitment,
        ),
        "subordinate": (
            float(ledger["subordinate_loan_draw"].sum()),
            config.sources.subordinate_loan_commitment,
        ),
        "preferred equity": (
            float(ledger["preferred_equity_draw"].sum()),
            config.sources.external_preferred_equity,
        ),
        "sponsor cure": (
            float(ledger["sponsor_cure_draw"].sum()),
            config.sources.additional_sponsor_equity_commitment,
        ),
    }
    for name, (drawn, commitment) in commitment_checks.items():
        if drawn > commitment + tolerance:
            raise LedgerInvariantError(f"{name} draws exceed commitment")

    if not math.isclose(
        float(ledger["sponsor_equity_draw"].sum()),
        config.sources.sponsor_common_equity,
        abs_tol=tolerance,
    ):
        raise LedgerInvariantError("base sponsor equity must be funded exactly once")

    if result.status == "completed":
        if len(ledger) != config.timeline.completion_month + 1:
            raise LedgerInvariantError("completed ledger must reach the completion month")
        if float(ledger["closing_cash"].min()) < -tolerance:
            raise LedgerInvariantError("completed ledger cannot contain negative cash")
        if abs(float(ledger.iloc[-1]["bridge_closing_balance"])) > tolerance:
            raise LedgerInvariantError("bridge must be repaid by completion")
        if not math.isclose(
            float(ledger["land_cost"].sum()),
            config.uses.land_and_acquisition,
            abs_tol=tolerance,
        ):
            raise LedgerInvariantError("land cost schedule does not use its budget")
        if not math.isclose(
            float(ledger["hard_cost"].sum()),
            config.uses.hard_cost,
            abs_tol=tolerance,
        ):
            raise LedgerInvariantError("hard-cost schedule does not use its budget")
        if not math.isclose(
            float(ledger["soft_cost"].sum()),
            config.uses.soft_cost,
            abs_tol=tolerance,
        ):
            raise LedgerInvariantError("soft-cost schedule does not use its budget")

        final_sources_drawn = float(
            ledger[
                [
                    "sponsor_equity_draw",
                    "sponsor_cure_draw",
                    "preferred_equity_draw",
                    "subordinate_loan_draw",
                    "senior_pf_draw",
                ]
            ]
            .sum()
            .sum()
        )
        expected_final_sources = result.development_cost_total + float(
            ledger.iloc[-1]["closing_cash"]
        )
        if not math.isclose(
            final_sources_drawn,
            expected_final_sources,
            abs_tol=tolerance,
        ):
            raise LedgerInvariantError(
                "final development sources must equal development costs plus closing cash"
            )
    elif result.status == "funding_default":
        if result.default_month != int(ledger.iloc[-1]["month"]):
            raise LedgerInvariantError("default month must match the terminal ledger row")
        if float(ledger.iloc[-1]["closing_cash"]) >= -tolerance:
            raise LedgerInvariantError("funding default must expose a negative cash balance")
    else:
        raise LedgerInvariantError(f"unknown ledger status: {result.status}")
