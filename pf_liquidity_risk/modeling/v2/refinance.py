"""Take-out capacity and refinancing-closing mechanics for V2."""

from dataclasses import dataclass
import math


def _positive(name: str, value: float) -> None:
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a finite positive number")


def _non_negative(name: str, value: float) -> None:
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be a finite non-negative number")


def _rate(name: str, value: float, *, allow_one: bool = True) -> None:
    upper_ok = value <= 1 if allow_one else value < 1
    if not math.isfinite(value) or value < 0 or not upper_ok:
        comparator = "between zero and one" if allow_one else "at least zero and below one"
        raise ValueError(f"{name} must be {comparator}")


@dataclass(frozen=True)
class TakeoutTerms:
    """Synthetic underwriting and pricing terms for an interest-only take-out."""

    capitalization_rate: float = 0.055
    maximum_ltv: float = 0.65
    minimum_debt_yield: float = 0.08
    annual_interest_rate: float = 0.055
    minimum_dscr: float = 1.40
    lender_commitment_cap: float = 1_000.0
    upfront_fee_rate: float = 0.01

    def __post_init__(self) -> None:
        _positive("capitalization_rate", self.capitalization_rate)
        _rate("maximum_ltv", self.maximum_ltv)
        _positive("minimum_debt_yield", self.minimum_debt_yield)
        _positive("annual_interest_rate", self.annual_interest_rate)
        _positive("minimum_dscr", self.minimum_dscr)
        _non_negative("lender_commitment_cap", self.lender_commitment_cap)
        _rate("upfront_fee_rate", self.upfront_fee_rate, allow_one=False)


@dataclass(frozen=True)
class TakeoutCapacity:
    """Constraint-by-constraint gross take-out capacity."""

    annual_underwritten_noi: float
    property_value: float
    ltv_capacity: float
    debt_yield_capacity: float
    dscr_capacity: float
    lender_commitment_cap: float
    gross_capacity: float
    binding_constraint: str


@dataclass(frozen=True)
class RefinanceDecision:
    """Closing result after project cash, take-out proceeds, and equity cure."""

    status: str
    capacity: TakeoutCapacity
    debt_payoff_requirement: float
    available_project_cash: float
    project_cash_applied: float
    required_gross_draw: float
    gross_takeout_draw: float
    takeout_fee: float
    net_takeout_proceeds: float
    gap_before_equity_cure: float
    sponsor_equity_cure: float
    funding_gap: float
    unused_project_cash: float


def size_takeout(
    annual_underwritten_noi: float,
    terms: TakeoutTerms | None = None,
) -> TakeoutCapacity:
    """Size an interest-only take-out at the most restrictive constraint."""

    terms = terms or TakeoutTerms()
    _non_negative("annual_underwritten_noi", annual_underwritten_noi)

    property_value = (
        annual_underwritten_noi / terms.capitalization_rate if annual_underwritten_noi > 0 else 0.0
    )
    capacities = {
        "ltv": property_value * terms.maximum_ltv,
        "debt_yield": (
            annual_underwritten_noi / terms.minimum_debt_yield
            if annual_underwritten_noi > 0
            else 0.0
        ),
        "dscr": (
            annual_underwritten_noi / (terms.annual_interest_rate * terms.minimum_dscr)
            if annual_underwritten_noi > 0
            else 0.0
        ),
        "lender_commitment": terms.lender_commitment_cap,
    }
    binding_constraint = min(capacities, key=capacities.get)
    return TakeoutCapacity(
        annual_underwritten_noi=annual_underwritten_noi,
        property_value=property_value,
        ltv_capacity=capacities["ltv"],
        debt_yield_capacity=capacities["debt_yield"],
        dscr_capacity=capacities["dscr"],
        lender_commitment_cap=terms.lender_commitment_cap,
        gross_capacity=capacities[binding_constraint],
        binding_constraint=binding_constraint,
    )


def fund_refinance(
    *,
    capacity: TakeoutCapacity,
    debt_payoff_requirement: float,
    available_project_cash: float,
    sponsor_equity_cure_commitment: float,
    terms: TakeoutTerms | None = None,
    tolerance: float = 1e-8,
) -> RefinanceDecision:
    """Determine whether a take-out can close without assuming undrawn capacity.

    Project cash is applied before new borrowing. A sponsor cure is funded only
    when the take-out plus the committed cure can complete the closing.
    """

    terms = terms or TakeoutTerms()
    for name, value in (
        ("debt_payoff_requirement", debt_payoff_requirement),
        ("available_project_cash", available_project_cash),
        ("sponsor_equity_cure_commitment", sponsor_equity_cure_commitment),
    ):
        _non_negative(name, value)
    _positive("tolerance", tolerance)

    project_cash_applied = min(available_project_cash, debt_payoff_requirement)
    payoff_after_cash = debt_payoff_requirement - project_cash_applied
    required_gross_draw = (
        payoff_after_cash / (1 - terms.upfront_fee_rate) if payoff_after_cash > 0 else 0.0
    )
    gross_takeout_draw = min(required_gross_draw, capacity.gross_capacity)
    takeout_fee = gross_takeout_draw * terms.upfront_fee_rate
    net_takeout_proceeds = gross_takeout_draw - takeout_fee
    gap_before_equity_cure = max(
        0.0,
        debt_payoff_requirement - project_cash_applied - net_takeout_proceeds,
    )

    can_close_with_cure = gap_before_equity_cure <= (sponsor_equity_cure_commitment + tolerance)
    sponsor_equity_cure = gap_before_equity_cure if can_close_with_cure else 0.0
    funding_gap = (
        max(0.0, gap_before_equity_cure - sponsor_equity_cure)
        if can_close_with_cure
        else gap_before_equity_cure
    )

    if funding_gap <= tolerance:
        status = "refi_success_with_cure" if sponsor_equity_cure > tolerance else "refi_success"
        funding_gap = 0.0
    else:
        status = "refi_shortfall"
        # A failed closing does not partially fund the new loan or deploy cure.
        gross_takeout_draw = 0.0
        takeout_fee = 0.0
        net_takeout_proceeds = 0.0
        project_cash_applied = 0.0
        sponsor_equity_cure = 0.0

    return RefinanceDecision(
        status=status,
        capacity=capacity,
        debt_payoff_requirement=debt_payoff_requirement,
        available_project_cash=available_project_cash,
        project_cash_applied=project_cash_applied,
        required_gross_draw=required_gross_draw,
        gross_takeout_draw=gross_takeout_draw,
        takeout_fee=takeout_fee,
        net_takeout_proceeds=net_takeout_proceeds,
        gap_before_equity_cure=gap_before_equity_cure,
        sponsor_equity_cure=sponsor_equity_cure,
        funding_gap=funding_gap,
        unused_project_cash=max(0.0, available_project_cash - project_cash_applied),
    )
