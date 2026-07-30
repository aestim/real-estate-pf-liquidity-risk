"""Sale valuation and debt/equity waterfall for V2."""

from dataclasses import dataclass
import math


def _finite_non_negative(name: str, value: float) -> None:
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be a finite non-negative number")


def _positive(name: str, value: float) -> None:
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a finite positive number")


@dataclass(frozen=True)
class SaleTerms:
    """Synthetic normal and distressed sale assumptions."""

    exit_capitalization_rate: float = 0.0575
    sale_cost_rate: float = 0.02
    distressed_cap_rate_spread: float = 0.01
    distressed_value_discount: float = 0.10
    preferred_annual_return: float = 0.08

    def __post_init__(self) -> None:
        _positive("exit_capitalization_rate", self.exit_capitalization_rate)
        _finite_non_negative("sale_cost_rate", self.sale_cost_rate)
        _finite_non_negative(
            "distressed_cap_rate_spread",
            self.distressed_cap_rate_spread,
        )
        _finite_non_negative(
            "distressed_value_discount",
            self.distressed_value_discount,
        )
        _finite_non_negative("preferred_annual_return", self.preferred_annual_return)
        if self.sale_cost_rate >= 1:
            raise ValueError("sale_cost_rate must be below one")
        if self.distressed_value_discount >= 1:
            raise ValueError("distressed_value_discount must be below one")


@dataclass(frozen=True)
class SaleWaterfallResult:
    """Value, costs, debt repayment, and equity distributions at sale."""

    sale_month: int
    distressed: bool
    annualized_noi: float
    capitalization_rate: float
    unadjusted_property_value: float
    gross_sale_proceeds: float
    sale_cost: float
    project_cash: float
    distributable_cash: float
    senior_debt_paid: float
    subordinate_debt_paid: float
    takeout_debt_paid: float
    lender_shortfall: float
    preferred_claim: float
    preferred_distribution: float
    sponsor_distribution: float


def run_sale_waterfall(
    *,
    annualized_noi: float,
    sale_month: int,
    project_cash: float,
    senior_debt: float,
    subordinate_debt: float,
    takeout_debt: float,
    preferred_equity_principal: float,
    preferred_funding_month: int,
    distressed: bool,
    terms: SaleTerms | None = None,
) -> SaleWaterfallResult:
    """Cap NOI and distribute cash in debt-then-equity priority."""

    terms = terms or SaleTerms()
    for name, value in (
        ("annualized_noi", annualized_noi),
        ("project_cash", project_cash),
        ("senior_debt", senior_debt),
        ("subordinate_debt", subordinate_debt),
        ("takeout_debt", takeout_debt),
        ("preferred_equity_principal", preferred_equity_principal),
    ):
        _finite_non_negative(name, value)
    if sale_month < preferred_funding_month:
        raise ValueError("sale_month cannot precede preferred_funding_month")

    capitalization_rate = terms.exit_capitalization_rate + (
        terms.distressed_cap_rate_spread if distressed else 0.0
    )
    unadjusted_property_value = annualized_noi / capitalization_rate if annualized_noi > 0 else 0.0
    gross_sale_proceeds = unadjusted_property_value * (
        1 - terms.distressed_value_discount if distressed else 1.0
    )
    sale_cost = gross_sale_proceeds * terms.sale_cost_rate
    distributable_cash = gross_sale_proceeds - sale_cost + project_cash

    remaining = distributable_cash
    takeout_debt_paid = min(takeout_debt, remaining)
    remaining -= takeout_debt_paid
    senior_debt_paid = min(senior_debt, remaining)
    remaining -= senior_debt_paid
    subordinate_debt_paid = min(subordinate_debt, remaining)
    remaining -= subordinate_debt_paid

    total_debt = senior_debt + subordinate_debt + takeout_debt
    total_debt_paid = senior_debt_paid + subordinate_debt_paid + takeout_debt_paid
    lender_shortfall = total_debt - total_debt_paid

    preferred_years = (sale_month - preferred_funding_month) / 12
    preferred_claim = (
        preferred_equity_principal * (1 + terms.preferred_annual_return) ** preferred_years
    )
    preferred_distribution = min(preferred_claim, remaining)
    remaining -= preferred_distribution
    sponsor_distribution = max(0.0, remaining)

    return SaleWaterfallResult(
        sale_month=sale_month,
        distressed=distressed,
        annualized_noi=annualized_noi,
        capitalization_rate=capitalization_rate,
        unadjusted_property_value=unadjusted_property_value,
        gross_sale_proceeds=gross_sale_proceeds,
        sale_cost=sale_cost,
        project_cash=project_cash,
        distributable_cash=distributable_cash,
        senior_debt_paid=senior_debt_paid,
        subordinate_debt_paid=subordinate_debt_paid,
        takeout_debt_paid=takeout_debt_paid,
        lender_shortfall=lender_shortfall,
        preferred_claim=preferred_claim,
        preferred_distribution=preferred_distribution,
        sponsor_distribution=sponsor_distribution,
    )
