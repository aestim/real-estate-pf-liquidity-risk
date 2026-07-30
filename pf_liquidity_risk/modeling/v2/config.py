"""Configuration contract for the deterministic V2 development ledger."""

from dataclasses import dataclass, field
import math


def _require_non_negative(values: dict[str, float]) -> None:
    for name, value in values.items():
        if not math.isfinite(value) or value < 0:
            raise ValueError(f"{name} must be a finite non-negative number")


@dataclass(frozen=True)
class DevelopmentUses:
    """Budgeted development uses, excluding bridge-loan refinancing flows."""

    land_and_acquisition: float = 300.0
    hard_cost: float = 500.0
    soft_cost: float = 80.0
    financing_cost_and_interest_reserve: float = 70.0
    contingency: float = 50.0

    def __post_init__(self) -> None:
        _require_non_negative(
            {
                "land_and_acquisition": self.land_and_acquisition,
                "hard_cost": self.hard_cost,
                "soft_cost": self.soft_cost,
                "financing_cost_and_interest_reserve": (self.financing_cost_and_interest_reserve),
                "contingency": self.contingency,
            }
        )

    @property
    def total(self) -> float:
        return (
            self.land_and_acquisition
            + self.hard_cost
            + self.soft_cost
            + self.financing_cost_and_interest_reserve
            + self.contingency
        )


@dataclass(frozen=True)
class DevelopmentSources:
    """Committed capital for the development stage.

    The bridge facility is temporary and is deliberately excluded from
    ``final_development_total`` to avoid counting the land financing twice.
    """

    sponsor_common_equity: float = 50.0
    external_preferred_equity: float = 100.0
    subordinate_loan_commitment: float = 100.0
    senior_pf_commitment: float = 750.0
    bridge_commitment: float = 300.0
    bridge_initial_draw: float = 250.0
    additional_sponsor_equity_commitment: float = 0.0

    def __post_init__(self) -> None:
        _require_non_negative(
            {
                "sponsor_common_equity": self.sponsor_common_equity,
                "external_preferred_equity": self.external_preferred_equity,
                "subordinate_loan_commitment": self.subordinate_loan_commitment,
                "senior_pf_commitment": self.senior_pf_commitment,
                "bridge_commitment": self.bridge_commitment,
                "bridge_initial_draw": self.bridge_initial_draw,
                "additional_sponsor_equity_commitment": (
                    self.additional_sponsor_equity_commitment
                ),
            }
        )
        if self.bridge_initial_draw > self.bridge_commitment:
            raise ValueError("bridge_initial_draw cannot exceed bridge_commitment")

    @property
    def final_development_total(self) -> float:
        """Committed base capital after cancelling the temporary bridge."""
        return (
            self.sponsor_common_equity
            + self.external_preferred_equity
            + self.subordinate_loan_commitment
            + self.senior_pf_commitment
        )


@dataclass(frozen=True)
class DevelopmentTimeline:
    """Deterministic milestone months for the first V2 slice."""

    land_acquisition_month: int = 0
    main_pf_close_month: int = 6
    construction_start_month: int = 7
    completion_month: int = 24

    def __post_init__(self) -> None:
        if self.land_acquisition_month != 0:
            raise ValueError("the V2 ledger requires land acquisition at Month 0")
        if not (
            self.land_acquisition_month
            < self.main_pf_close_month
            < self.construction_start_month
            <= self.completion_month
        ):
            raise ValueError("timeline milestones must be strictly ordered")

    @property
    def predevelopment_months(self) -> tuple[int, ...]:
        return tuple(range(1, self.main_pf_close_month))

    @property
    def construction_months(self) -> tuple[int, ...]:
        return tuple(range(self.construction_start_month, self.completion_month + 1))


@dataclass(frozen=True)
class FinancingTerms:
    """Synthetic rates used to prove the ledger mechanics.

    These defaults are deterministic calculation fixtures, not current market
    quotes.  Later calibration must replace them with sourced assumptions.
    Interest is charged monthly on the opening principal balance.
    """

    bridge_annual_rate: float = 0.08
    senior_pf_annual_rate: float = 0.055
    subordinate_annual_rate: float = 0.09
    bridge_upfront_fee: float = 2.0
    main_pf_upfront_fee: float = 3.0

    def __post_init__(self) -> None:
        _require_non_negative(
            {
                "bridge_annual_rate": self.bridge_annual_rate,
                "senior_pf_annual_rate": self.senior_pf_annual_rate,
                "subordinate_annual_rate": self.subordinate_annual_rate,
                "bridge_upfront_fee": self.bridge_upfront_fee,
                "main_pf_upfront_fee": self.main_pf_upfront_fee,
            }
        )


def _default_hard_cost_weights() -> tuple[float, ...]:
    """An 18-month deterministic S-curve summing to one."""
    return (
        0.02,
        0.03,
        0.04,
        0.05,
        0.06,
        0.07,
        0.08,
        0.09,
        0.09,
        0.09,
        0.09,
        0.08,
        0.07,
        0.06,
        0.04,
        0.02,
        0.01,
        0.01,
    )


@dataclass(frozen=True)
class DevelopmentLedgerConfig:
    """Complete deterministic contract for Months 0 through completion."""

    uses: DevelopmentUses = field(default_factory=DevelopmentUses)
    sources: DevelopmentSources = field(default_factory=DevelopmentSources)
    timeline: DevelopmentTimeline = field(default_factory=DevelopmentTimeline)
    financing: FinancingTerms = field(default_factory=FinancingTerms)
    predevelopment_soft_cost: float = 20.0
    hard_cost_weights: tuple[float, ...] = field(default_factory=_default_hard_cost_weights)
    amount_tolerance: float = 1e-8

    def __post_init__(self) -> None:
        _require_non_negative(
            {
                "predevelopment_soft_cost": self.predevelopment_soft_cost,
                "amount_tolerance": self.amount_tolerance,
            }
        )
        if self.amount_tolerance == 0:
            raise ValueError("amount_tolerance must be positive")
        if self.predevelopment_soft_cost > self.uses.soft_cost:
            raise ValueError("predevelopment_soft_cost cannot exceed the soft-cost budget")
        if not math.isclose(
            self.uses.total,
            self.sources.final_development_total,
            abs_tol=self.amount_tolerance,
        ):
            raise ValueError("final development sources must equal budgeted development uses")
        if not math.isclose(
            self.sources.sponsor_common_equity + self.sources.bridge_initial_draw,
            self.uses.land_and_acquisition,
            abs_tol=self.amount_tolerance,
        ):
            raise ValueError(
                "Month 0 sponsor equity plus initial bridge draw must fund the land use"
            )
        if len(self.hard_cost_weights) != len(self.timeline.construction_months):
            raise ValueError("hard_cost_weights must contain one weight per construction month")
        if any(weight < 0 or not math.isfinite(weight) for weight in self.hard_cost_weights):
            raise ValueError("hard_cost_weights must be finite non-negative numbers")
        if not math.isclose(sum(self.hard_cost_weights), 1.0, abs_tol=self.amount_tolerance):
            raise ValueError("hard_cost_weights must sum to one")


def build_base_case_config() -> DevelopmentLedgerConfig:
    """Return the synthetic, contract-aligned V2 base case."""
    return DevelopmentLedgerConfig()
