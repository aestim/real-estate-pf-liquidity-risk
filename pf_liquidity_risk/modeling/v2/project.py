"""End-to-end deterministic V2 project cash-flow engine."""

from dataclasses import dataclass, field
import math
from typing import Any

import pandas as pd

from pf_liquidity_risk.modeling.v2.config import (
    DevelopmentLedgerConfig,
    build_base_case_config,
)
from pf_liquidity_risk.modeling.v2.leasing import (
    OperatingLedgerConfig,
    build_base_operating_config,
    build_operating_ledger,
)
from pf_liquidity_risk.modeling.v2.ledger import build_development_ledger
from pf_liquidity_risk.modeling.v2.refinance import (
    RefinanceDecision,
    TakeoutTerms,
    fund_refinance,
    size_takeout,
)
from pf_liquidity_risk.modeling.v2.returns import (
    periodic_irr,
    realized_equity_multiple,
)
from pf_liquidity_risk.modeling.v2.waterfall import (
    SaleTerms,
    SaleWaterfallResult,
    run_sale_waterfall,
)


def _finite_non_negative(name: str, value: float) -> None:
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be a finite non-negative number")


@dataclass(frozen=True)
class ResolutionTerms:
    """Sponsor support and one permitted development-loan extension."""

    sponsor_operating_cure_commitment: float = 25.0
    sponsor_refi_cure_commitment: float = 25.0
    extension_months: int = 6
    extension_annual_rate_step_up: float = 0.02
    extension_fee_rate: float = 0.01

    def __post_init__(self) -> None:
        _finite_non_negative(
            "sponsor_operating_cure_commitment",
            self.sponsor_operating_cure_commitment,
        )
        _finite_non_negative(
            "sponsor_refi_cure_commitment",
            self.sponsor_refi_cure_commitment,
        )
        if self.extension_months <= 0:
            raise ValueError("extension_months must be positive")
        _finite_non_negative(
            "extension_annual_rate_step_up",
            self.extension_annual_rate_step_up,
        )
        _finite_non_negative("extension_fee_rate", self.extension_fee_rate)
        if self.extension_fee_rate >= 1:
            raise ValueError("extension_fee_rate must be below one")


@dataclass(frozen=True)
class ProjectV2Config:
    """All deterministic inputs needed for an end-to-end V2 path."""

    development: DevelopmentLedgerConfig = field(default_factory=build_base_case_config)
    operating: OperatingLedgerConfig = field(default_factory=build_base_operating_config)
    takeout: TakeoutTerms = field(default_factory=TakeoutTerms)
    sale: SaleTerms = field(default_factory=SaleTerms)
    resolution: ResolutionTerms = field(default_factory=ResolutionTerms)

    def __post_init__(self) -> None:
        if self.operating.operations_start_month != self.development.timeline.completion_month + 1:
            raise ValueError("operations must begin one month after completion")
        extension_refi_month = self.operating.underwriting_month + self.resolution.extension_months
        if extension_refi_month > self.operating.operations_end_month:
            raise ValueError("operating period must include the extension refi month")


@dataclass(frozen=True)
class ProjectV2Result:
    """Terminal project result with transparent monthly equity cash flows."""

    status: str
    terminal_month: int
    ledger: pd.DataFrame
    refinance_attempts: tuple[RefinanceDecision, ...]
    sale: SaleWaterfallResult | None
    sponsor_irr: float
    combined_equity_irr: float
    sponsor_equity_multiple: float
    combined_equity_multiple: float
    sponsor_equity_invested: float
    preferred_equity_invested: float
    sponsor_distribution: float
    preferred_distribution: float
    refi_funding_gap: float
    lender_shortfall: float


class ProjectLedgerInvariantError(RuntimeError):
    """Raised when the integrated monthly project ledger does not reconcile."""


def build_base_project_config() -> ProjectV2Config:
    """Return the synthetic end-to-end V2 base case."""
    return ProjectV2Config()


def _blank_row(month: int, phase: str, event: str = "") -> dict[str, Any]:
    return {
        "month": month,
        "phase": phase,
        "event": event,
        "property_noi": 0.0,
        "opening_cash": 0.0,
        "sponsor_equity_draw": 0.0,
        "sponsor_cure_draw": 0.0,
        "capitalized_default_claim": 0.0,
        "preferred_equity_draw": 0.0,
        "bridge_loan_draw": 0.0,
        "subordinate_loan_draw": 0.0,
        "senior_pf_draw": 0.0,
        "takeout_draw": 0.0,
        "sale_proceeds": 0.0,
        "total_sources": 0.0,
        "development_cost_uses": 0.0,
        "bridge_repayment": 0.0,
        "interest_expense": 0.0,
        "extension_fee": 0.0,
        "takeout_fee": 0.0,
        "senior_repayment": 0.0,
        "subordinate_repayment": 0.0,
        "takeout_repayment": 0.0,
        "sale_cost": 0.0,
        "preferred_distribution": 0.0,
        "sponsor_distribution": 0.0,
        "total_uses": 0.0,
        "closing_cash": 0.0,
        "bridge_opening_balance": 0.0,
        "bridge_closing_balance": 0.0,
        "senior_opening_balance": 0.0,
        "senior_closing_balance": 0.0,
        "subordinate_opening_balance": 0.0,
        "subordinate_closing_balance": 0.0,
        "takeout_opening_balance": 0.0,
        "takeout_closing_balance": 0.0,
        "sponsor_equity_cash_flow": 0.0,
        "preferred_equity_cash_flow": 0.0,
        "combined_equity_cash_flow": 0.0,
    }


def _development_rows(config: ProjectV2Config) -> tuple[list[dict[str, Any]], str]:
    result = build_development_ledger(config.development)
    rows: list[dict[str, Any]] = []
    for source in result.ledger.to_dict(orient="records"):
        row = _blank_row(int(source["month"]), str(source["phase"]))
        row.update(
            {
                "opening_cash": source["opening_cash"],
                "sponsor_equity_draw": source["sponsor_equity_draw"],
                "sponsor_cure_draw": source["sponsor_cure_draw"],
                "preferred_equity_draw": source["preferred_equity_draw"],
                "bridge_loan_draw": source["bridge_loan_draw"],
                "subordinate_loan_draw": source["subordinate_loan_draw"],
                "senior_pf_draw": source["senior_pf_draw"],
                "total_sources": source["total_sources"],
                "development_cost_uses": source["development_cost_uses"],
                "bridge_repayment": source["bridge_repayment"],
                "interest_expense": (
                    source["bridge_interest"]
                    + source["senior_interest"]
                    + source["subordinate_interest"]
                ),
                "total_uses": source["total_uses"],
                "closing_cash": source["closing_cash"],
                "bridge_opening_balance": source["bridge_opening_balance"],
                "bridge_closing_balance": source["bridge_closing_balance"],
                "senior_opening_balance": source["senior_opening_balance"],
                "senior_closing_balance": source["senior_closing_balance"],
                "subordinate_opening_balance": source["subordinate_opening_balance"],
                "subordinate_closing_balance": source["subordinate_closing_balance"],
                "sponsor_equity_cash_flow": -(
                    source["sponsor_equity_draw"] + source["sponsor_cure_draw"]
                ),
                "preferred_equity_cash_flow": -source["preferred_equity_draw"],
            }
        )
        row["combined_equity_cash_flow"] = (
            row["sponsor_equity_cash_flow"] + row["preferred_equity_cash_flow"]
        )
        rows.append(row)
    return rows, result.status


def _annualized_trailing_noi(
    operating_ledger: pd.DataFrame,
    *,
    month: int,
    lookback_months: int,
) -> float:
    start = month - lookback_months + 1
    monthly_noi = operating_ledger.loc[
        operating_ledger["month"].between(start, month),
        "property_noi",
    ]
    if len(monthly_noi) != lookback_months:
        raise ValueError("operating ledger lacks the required NOI lookback")
    return max(0.0, float(monthly_noi.mean()) * 12)


def _finalize_result(
    *,
    status: str,
    rows: list[dict[str, Any]],
    refinance_attempts: list[RefinanceDecision],
    sale: SaleWaterfallResult | None,
) -> ProjectV2Result:
    ledger = pd.DataFrame(rows)
    sponsor_flows = ledger["sponsor_equity_cash_flow"].tolist()
    preferred_flows = ledger["preferred_equity_cash_flow"].tolist()
    combined_flows = ledger["combined_equity_cash_flow"].tolist()

    sponsor_irr = periodic_irr(sponsor_flows)
    combined_irr = periodic_irr(combined_flows)
    sponsor_distribution = float(ledger["sponsor_distribution"].sum())
    preferred_distribution = float(ledger["preferred_distribution"].sum())
    lender_shortfall = sale.lender_shortfall if sale is not None else 0.0
    refi_funding_gap = (
        refinance_attempts[-1].funding_gap
        if refinance_attempts and refinance_attempts[-1].status == "refi_shortfall"
        else 0.0
    )

    result = ProjectV2Result(
        status=status,
        terminal_month=int(ledger.iloc[-1]["month"]),
        ledger=ledger,
        refinance_attempts=tuple(refinance_attempts),
        sale=sale,
        sponsor_irr=sponsor_irr if sponsor_irr is not None else -1.0,
        combined_equity_irr=combined_irr if combined_irr is not None else -1.0,
        sponsor_equity_multiple=realized_equity_multiple(sponsor_flows),
        combined_equity_multiple=realized_equity_multiple(combined_flows),
        sponsor_equity_invested=-sum(min(value, 0.0) for value in sponsor_flows),
        preferred_equity_invested=-sum(min(value, 0.0) for value in preferred_flows),
        sponsor_distribution=sponsor_distribution,
        preferred_distribution=preferred_distribution,
        refi_funding_gap=refi_funding_gap,
        lender_shortfall=lender_shortfall,
    )
    validate_project_ledger(result)
    return result


def run_project(
    config: ProjectV2Config | None = None,
) -> ProjectV2Result:
    """Run one deterministic V2 path through refinancing and sale."""

    config = config or build_base_project_config()
    rows, development_status = _development_rows(config)
    if development_status == "funding_default":
        return _finalize_result(
            status="development_default",
            rows=rows,
            refinance_attempts=[],
            sale=None,
        )

    operating = build_operating_ledger(config.operating).ledger
    operating_by_month = operating.set_index("month")

    last_development = rows[-1]
    cash = float(last_development["closing_cash"])
    senior_balance = float(last_development["senior_closing_balance"])
    subordinate_balance = float(last_development["subordinate_closing_balance"])
    takeout_balance = 0.0
    senior_drawn = float(sum(row["senior_pf_draw"] for row in rows))
    operating_cure_used = 0.0
    refi_cure_used = 0.0

    refinance_attempts: list[RefinanceDecision] = []
    refi_succeeded = False
    extension_active = False
    extension_used = False
    success_after_extension = False
    sale_result: SaleWaterfallResult | None = None
    terminal_status = ""

    initial_refi_month = config.operating.underwriting_month
    extended_refi_month = initial_refi_month + config.resolution.extension_months

    for month in range(
        config.operating.operations_start_month,
        config.operating.operations_end_month + 1,
    ):
        op = operating_by_month.loc[month]
        phase = "operations" if refi_succeeded else "lease_up"
        row = _blank_row(month, phase)
        row["opening_cash"] = cash
        row["property_noi"] = float(op["property_noi"])
        row["senior_opening_balance"] = senior_balance
        row["subordinate_opening_balance"] = subordinate_balance
        row["takeout_opening_balance"] = takeout_balance

        rate_step_up = config.resolution.extension_annual_rate_step_up if extension_active else 0.0
        if refi_succeeded:
            interest_expense = takeout_balance * config.takeout.annual_interest_rate / 12
        else:
            interest_expense = (
                senior_balance
                * (config.development.financing.senior_pf_annual_rate + rate_step_up)
                / 12
                + subordinate_balance
                * (config.development.financing.subordinate_annual_rate + rate_step_up)
                / 12
            )
        row["interest_expense"] = interest_expense

        available_cash = cash + row["property_noi"] - interest_expense
        if available_cash < 0:
            shortfall = -available_cash
            if not refi_succeeded:
                remaining_senior = config.development.sources.senior_pf_commitment - senior_drawn
                senior_draw = min(shortfall, max(0.0, remaining_senior))
                row["senior_pf_draw"] += senior_draw
                senior_balance += senior_draw
                senior_drawn += senior_draw
                available_cash += senior_draw
                shortfall -= senior_draw

            if shortfall > 0:
                remaining_cure = (
                    config.resolution.sponsor_operating_cure_commitment - operating_cure_used
                )
                sponsor_cure = min(shortfall, max(0.0, remaining_cure))
                row["sponsor_cure_draw"] += sponsor_cure
                row["sponsor_equity_cash_flow"] -= sponsor_cure
                operating_cure_used += sponsor_cure
                available_cash += sponsor_cure

        if available_cash < -config.development.amount_tolerance:
            # Unpaid current-period interest is not forgiven at default. It
            # becomes part of the senior lender's claim immediately before the
            # collateral sale, with an equal non-cash funding source in the
            # integrated ledger.
            default_claim = -available_cash
            row["capitalized_default_claim"] = default_claim
            senior_balance += default_claim
            available_cash += default_claim
            annual_noi = _annualized_trailing_noi(
                operating,
                month=month,
                lookback_months=min(
                    config.operating.underwriting_lookback_months,
                    month - config.operating.operations_start_month + 1,
                ),
            )
            sale_result = run_sale_waterfall(
                annualized_noi=annual_noi,
                sale_month=month,
                project_cash=max(0.0, available_cash),
                senior_debt=senior_balance,
                subordinate_debt=subordinate_balance,
                takeout_debt=takeout_balance,
                preferred_equity_principal=(config.development.sources.external_preferred_equity),
                preferred_funding_month=(config.development.timeline.main_pf_close_month),
                distressed=True,
                terms=config.sale,
            )
            terminal_status = "operating_default_sale"
        elif not refi_succeeded and month in {initial_refi_month, extended_refi_month}:
            annual_noi = _annualized_trailing_noi(
                operating,
                month=month,
                lookback_months=config.operating.underwriting_lookback_months,
            )
            capacity = size_takeout(annual_noi, config.takeout)
            decision = fund_refinance(
                capacity=capacity,
                debt_payoff_requirement=senior_balance + subordinate_balance,
                available_project_cash=max(0.0, available_cash),
                sponsor_equity_cure_commitment=(
                    config.resolution.sponsor_refi_cure_commitment - refi_cure_used
                ),
                terms=config.takeout,
                tolerance=config.development.amount_tolerance,
            )
            refinance_attempts.append(decision)

            if decision.status != "refi_shortfall":
                row["event"] = decision.status
                row["takeout_draw"] = decision.gross_takeout_draw
                row["takeout_fee"] = decision.takeout_fee
                row["senior_repayment"] = senior_balance
                row["subordinate_repayment"] = subordinate_balance
                row["sponsor_cure_draw"] += decision.sponsor_equity_cure
                row["sponsor_equity_cash_flow"] -= decision.sponsor_equity_cure
                refi_cure_used += decision.sponsor_equity_cure

                available_cash += (
                    decision.gross_takeout_draw
                    + decision.sponsor_equity_cure
                    - decision.takeout_fee
                    - senior_balance
                    - subordinate_balance
                )
                takeout_balance = decision.gross_takeout_draw
                senior_balance = 0.0
                subordinate_balance = 0.0
                refi_succeeded = True
                success_after_extension = extension_used
                extension_active = False
            elif month == initial_refi_month:
                row["event"] = "refi_shortfall_extension"
                extension_used = True
                extension_active = True
                extension_fee = (
                    senior_balance + subordinate_balance
                ) * config.resolution.extension_fee_rate
                row["extension_fee"] = extension_fee
                available_cash -= extension_fee

                if available_cash < 0:
                    shortfall = -available_cash
                    remaining_senior = (
                        config.development.sources.senior_pf_commitment - senior_drawn
                    )
                    senior_draw = min(shortfall, max(0.0, remaining_senior))
                    row["senior_pf_draw"] += senior_draw
                    senior_balance += senior_draw
                    senior_drawn += senior_draw
                    available_cash += senior_draw
                    shortfall -= senior_draw
                if available_cash < 0:
                    remaining_cure = (
                        config.resolution.sponsor_operating_cure_commitment - operating_cure_used
                    )
                    sponsor_cure = min(-available_cash, max(0.0, remaining_cure))
                    row["sponsor_cure_draw"] += sponsor_cure
                    row["sponsor_equity_cash_flow"] -= sponsor_cure
                    operating_cure_used += sponsor_cure
                    available_cash += sponsor_cure

                if available_cash < -config.development.amount_tolerance:
                    # The unpaid extension fee/current-period debt service is
                    # capitalized into the senior claim before liquidation.
                    default_claim = -available_cash
                    row["capitalized_default_claim"] = default_claim
                    senior_balance += default_claim
                    available_cash += default_claim
                    annual_noi = _annualized_trailing_noi(
                        operating,
                        month=month,
                        lookback_months=(config.operating.underwriting_lookback_months),
                    )
                    sale_result = run_sale_waterfall(
                        annualized_noi=annual_noi,
                        sale_month=month,
                        project_cash=0.0,
                        senior_debt=senior_balance,
                        subordinate_debt=subordinate_balance,
                        takeout_debt=0.0,
                        preferred_equity_principal=(
                            config.development.sources.external_preferred_equity
                        ),
                        preferred_funding_month=(config.development.timeline.main_pf_close_month),
                        distressed=True,
                        terms=config.sale,
                    )
                    terminal_status = "extension_fee_default_sale"
            else:
                row["event"] = "refi_shortfall_distressed_sale"
                sale_result = run_sale_waterfall(
                    annualized_noi=annual_noi,
                    sale_month=month,
                    project_cash=max(0.0, available_cash),
                    senior_debt=senior_balance,
                    subordinate_debt=subordinate_balance,
                    takeout_debt=0.0,
                    preferred_equity_principal=(
                        config.development.sources.external_preferred_equity
                    ),
                    preferred_funding_month=(config.development.timeline.main_pf_close_month),
                    distressed=True,
                    terms=config.sale,
                )
                terminal_status = "distressed_sale"

        if sale_result is None and month == config.operating.operations_end_month:
            annual_noi = _annualized_trailing_noi(
                operating,
                month=month,
                lookback_months=config.operating.underwriting_lookback_months,
            )
            sale_result = run_sale_waterfall(
                annualized_noi=annual_noi,
                sale_month=month,
                project_cash=max(0.0, available_cash),
                senior_debt=senior_balance,
                subordinate_debt=subordinate_balance,
                takeout_debt=takeout_balance,
                preferred_equity_principal=(config.development.sources.external_preferred_equity),
                preferred_funding_month=(config.development.timeline.main_pf_close_month),
                distressed=not refi_succeeded,
                terms=config.sale,
            )
            if refi_succeeded:
                terminal_status = "exit_after_extension" if success_after_extension else "exit"
            else:
                terminal_status = "unrefinanced_distressed_sale"

        if sale_result is not None:
            row["event"] = row["event"] or (
                "distressed_sale" if sale_result.distressed else "normal_exit"
            )
            row["sale_proceeds"] = sale_result.gross_sale_proceeds
            row["sale_cost"] = sale_result.sale_cost
            row["senior_repayment"] += sale_result.senior_debt_paid
            row["subordinate_repayment"] += sale_result.subordinate_debt_paid
            row["takeout_repayment"] = sale_result.takeout_debt_paid
            row["preferred_distribution"] = sale_result.preferred_distribution
            row["sponsor_distribution"] = sale_result.sponsor_distribution
            row["preferred_equity_cash_flow"] += sale_result.preferred_distribution
            row["sponsor_equity_cash_flow"] += sale_result.sponsor_distribution

            senior_balance -= sale_result.senior_debt_paid
            subordinate_balance -= sale_result.subordinate_debt_paid
            takeout_balance -= sale_result.takeout_debt_paid
            available_cash = 0.0

        row["total_sources"] = (
            row["property_noi"]
            + row["sponsor_cure_draw"]
            + row["capitalized_default_claim"]
            + row["senior_pf_draw"]
            + row["takeout_draw"]
            + row["sale_proceeds"]
        )
        row["total_uses"] = (
            row["interest_expense"]
            + row["extension_fee"]
            + row["takeout_fee"]
            + row["senior_repayment"]
            + row["subordinate_repayment"]
            + row["takeout_repayment"]
            + row["sale_cost"]
            + row["preferred_distribution"]
            + row["sponsor_distribution"]
        )
        if abs(available_cash) <= config.development.amount_tolerance:
            available_cash = 0.0
        row["closing_cash"] = available_cash
        row["senior_closing_balance"] = max(0.0, senior_balance)
        row["subordinate_closing_balance"] = max(0.0, subordinate_balance)
        row["takeout_closing_balance"] = max(0.0, takeout_balance)
        row["combined_equity_cash_flow"] = (
            row["sponsor_equity_cash_flow"] + row["preferred_equity_cash_flow"]
        )
        rows.append(row)
        cash = available_cash

        if sale_result is not None:
            break

    if not terminal_status:
        terminal_status = "survived_without_exit"
    return _finalize_result(
        status=terminal_status,
        rows=rows,
        refinance_attempts=refinance_attempts,
        sale=sale_result,
    )


def validate_project_ledger(result: ProjectV2Result, tolerance: float = 1e-7) -> None:
    """Validate integrated cash and equity cash-flow identities."""

    ledger = result.ledger
    if ledger.empty:
        raise ProjectLedgerInvariantError("project ledger cannot be empty")

    expected_cash = ledger["opening_cash"] + ledger["total_sources"] - ledger["total_uses"]
    differences = (ledger["closing_cash"] - expected_cash).abs()
    if bool((differences > tolerance).any()):
        row = int(differences.idxmax())
        raise ProjectLedgerInvariantError(f"project cash does not reconcile at row {row}")

    expected_combined = ledger["sponsor_equity_cash_flow"] + ledger["preferred_equity_cash_flow"]
    if bool(((ledger["combined_equity_cash_flow"] - expected_combined).abs() > tolerance).any()):
        raise ProjectLedgerInvariantError("combined equity cash flow does not reconcile")

    debt_columns = [
        "bridge_closing_balance",
        "senior_closing_balance",
        "subordinate_closing_balance",
        "takeout_closing_balance",
    ]
    if bool((ledger[debt_columns] < -tolerance).any().any()):
        raise ProjectLedgerInvariantError("debt balances cannot be negative")

    if result.sale is not None and abs(float(ledger.iloc[-1]["closing_cash"])) > tolerance:
        raise ProjectLedgerInvariantError("terminal sale must distribute all project cash")
