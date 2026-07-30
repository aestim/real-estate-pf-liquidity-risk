"""Bottom-up lease-up and property-NOI ledger for the deterministic V2 case."""

from dataclasses import dataclass, field
import math
from typing import Any

import pandas as pd


def _finite_non_negative(name: str, value: float) -> None:
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be a finite non-negative number")


def _rate_between_zero_and_one(name: str, value: float) -> None:
    if not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError(f"{name} must be between zero and one")


@dataclass(frozen=True)
class LeaseSegment:
    """One simplified rent-roll segment.

    ``rent_free_months`` applies to all occupied rent in the segment during the
    initial operating months.  Individual-tenant lease cohorts are deferred to
    a later extension.
    """

    name: str
    leasable_area: float
    monthly_base_rent_per_area: float
    initial_occupancy: float
    stabilized_occupancy: float
    lease_up_months: int
    rent_free_months: int = 0

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("lease segment name cannot be empty")
        if not math.isfinite(self.leasable_area) or self.leasable_area <= 0:
            raise ValueError("leasable_area must be a finite positive number")
        _finite_non_negative(
            "monthly_base_rent_per_area",
            self.monthly_base_rent_per_area,
        )
        _rate_between_zero_and_one("initial_occupancy", self.initial_occupancy)
        _rate_between_zero_and_one("stabilized_occupancy", self.stabilized_occupancy)
        if self.initial_occupancy > self.stabilized_occupancy:
            raise ValueError("initial_occupancy cannot exceed stabilized_occupancy")
        if self.lease_up_months <= 0:
            raise ValueError("lease_up_months must be positive")
        if self.rent_free_months < 0:
            raise ValueError("rent_free_months cannot be negative")


def _default_anchor_segment() -> LeaseSegment:
    return LeaseSegment(
        name="anchor",
        leasable_area=4_000.0,
        monthly_base_rent_per_area=0.0009,
        initial_occupancy=1.0,
        stabilized_occupancy=1.0,
        lease_up_months=1,
        rent_free_months=2,
    )


def _default_non_anchor_segment() -> LeaseSegment:
    return LeaseSegment(
        name="non_anchor",
        leasable_area=6_000.0,
        monthly_base_rent_per_area=0.0010,
        initial_occupancy=0.20,
        stabilized_occupancy=0.95,
        lease_up_months=12,
        rent_free_months=0,
    )


@dataclass(frozen=True)
class OperatingLedgerConfig:
    """Synthetic operating assumptions for Months 25 through 60."""

    operations_start_month: int = 25
    operations_end_month: int = 60
    underwriting_month: int = 36
    underwriting_lookback_months: int = 3
    anchor: LeaseSegment = field(default_factory=_default_anchor_segment)
    non_anchor: LeaseSegment = field(default_factory=_default_non_anchor_segment)
    annual_rent_growth: float = 0.02
    collection_loss_rate: float = 0.01
    other_income_rate_on_collected_rent: float = 0.02
    fixed_monthly_operating_expense: float = 1.26
    variable_operating_expense_rate: float = 0.20
    amount_tolerance: float = 1e-8

    def __post_init__(self) -> None:
        if self.operations_start_month < 0:
            raise ValueError("operations_start_month cannot be negative")
        if self.operations_end_month < self.operations_start_month:
            raise ValueError("operations_end_month cannot precede operations_start_month")
        if not self.operations_start_month <= self.underwriting_month <= self.operations_end_month:
            raise ValueError("underwriting_month must be within the operating period")
        if self.underwriting_lookback_months <= 0:
            raise ValueError("underwriting_lookback_months must be positive")
        first_underwriting_month = self.underwriting_month - self.underwriting_lookback_months + 1
        if first_underwriting_month < self.operations_start_month:
            raise ValueError("underwriting lookback begins before operations")
        if self.anchor.name == self.non_anchor.name:
            raise ValueError("lease segment names must be unique")

        _finite_non_negative("annual_rent_growth", self.annual_rent_growth)
        _rate_between_zero_and_one("collection_loss_rate", self.collection_loss_rate)
        _rate_between_zero_and_one(
            "other_income_rate_on_collected_rent",
            self.other_income_rate_on_collected_rent,
        )
        _finite_non_negative(
            "fixed_monthly_operating_expense",
            self.fixed_monthly_operating_expense,
        )
        _rate_between_zero_and_one(
            "variable_operating_expense_rate",
            self.variable_operating_expense_rate,
        )
        if not math.isfinite(self.amount_tolerance) or self.amount_tolerance <= 0:
            raise ValueError("amount_tolerance must be a finite positive number")

    @property
    def total_leasable_area(self) -> float:
        return self.anchor.leasable_area + self.non_anchor.leasable_area


@dataclass(frozen=True)
class OperatingLedgerResult:
    """Monthly operating ledger and the NOI used at the take-out test."""

    ledger: pd.DataFrame
    underwriting_month: int
    underwritten_monthly_noi: float
    underwritten_annual_noi: float
    first_positive_noi_month: int | None


class OperatingLedgerInvariantError(RuntimeError):
    """Raised when revenue, expense, or NOI calculations do not reconcile."""


def build_base_operating_config() -> OperatingLedgerConfig:
    """Return the synthetic V2 lease-up fixture."""
    return OperatingLedgerConfig()


def _occupancy(segment: LeaseSegment, elapsed_months: int) -> float:
    if segment.lease_up_months == 1:
        return segment.stabilized_occupancy
    if elapsed_months >= segment.lease_up_months - 1:
        return segment.stabilized_occupancy
    progress = elapsed_months / (segment.lease_up_months - 1)
    return (
        segment.initial_occupancy
        + (segment.stabilized_occupancy - segment.initial_occupancy) * progress
    )


def _segment_values(
    segment: LeaseSegment,
    *,
    elapsed_months: int,
    rent_multiplier: float,
) -> dict[str, float]:
    occupancy = _occupancy(segment, elapsed_months)
    gross_potential_rent = (
        segment.leasable_area * segment.monthly_base_rent_per_area * rent_multiplier
    )
    occupied_rent = gross_potential_rent * occupancy
    rent_free_concession = occupied_rent if elapsed_months < segment.rent_free_months else 0.0
    billed_rent = occupied_rent - rent_free_concession
    return {
        "occupancy": occupancy,
        "occupied_area": segment.leasable_area * occupancy,
        "gross_potential_rent": gross_potential_rent,
        "occupied_rent": occupied_rent,
        "rent_free_concession": rent_free_concession,
        "billed_rent": billed_rent,
    }


def build_operating_ledger(
    config: OperatingLedgerConfig | None = None,
) -> OperatingLedgerResult:
    """Build a deterministic lease-up ledger from opening through exit month."""

    config = config or build_base_operating_config()
    rows: list[dict[str, Any]] = []

    for month in range(config.operations_start_month, config.operations_end_month + 1):
        elapsed_months = month - config.operations_start_month
        lease_year = elapsed_months // 12
        rent_multiplier = (1 + config.annual_rent_growth) ** lease_year

        anchor = _segment_values(
            config.anchor,
            elapsed_months=elapsed_months,
            rent_multiplier=rent_multiplier,
        )
        non_anchor = _segment_values(
            config.non_anchor,
            elapsed_months=elapsed_months,
            rent_multiplier=rent_multiplier,
        )

        occupied_area = anchor["occupied_area"] + non_anchor["occupied_area"]
        physical_occupancy = occupied_area / config.total_leasable_area
        gross_potential_rent = anchor["gross_potential_rent"] + non_anchor["gross_potential_rent"]
        occupied_rent = anchor["occupied_rent"] + non_anchor["occupied_rent"]
        rent_free_concession = anchor["rent_free_concession"] + non_anchor["rent_free_concession"]
        billed_rent = anchor["billed_rent"] + non_anchor["billed_rent"]
        collection_loss = billed_rent * config.collection_loss_rate
        collected_rent = billed_rent - collection_loss
        other_income = collected_rent * config.other_income_rate_on_collected_rent
        effective_property_revenue = collected_rent + other_income
        variable_operating_expense = (
            effective_property_revenue * config.variable_operating_expense_rate
        )
        fixed_operating_expense = config.fixed_monthly_operating_expense
        property_operating_expense = fixed_operating_expense + variable_operating_expense
        property_noi = effective_property_revenue - property_operating_expense

        rows.append(
            {
                "month": month,
                "lease_year": lease_year,
                "rent_multiplier": rent_multiplier,
                "anchor_occupancy": anchor["occupancy"],
                "non_anchor_occupancy": non_anchor["occupancy"],
                "physical_occupancy": physical_occupancy,
                "anchor_occupied_area": anchor["occupied_area"],
                "non_anchor_occupied_area": non_anchor["occupied_area"],
                "occupied_area": occupied_area,
                "anchor_gross_potential_rent": anchor["gross_potential_rent"],
                "non_anchor_gross_potential_rent": non_anchor["gross_potential_rent"],
                "gross_potential_rent": gross_potential_rent,
                "anchor_occupied_rent": anchor["occupied_rent"],
                "non_anchor_occupied_rent": non_anchor["occupied_rent"],
                "occupied_rent": occupied_rent,
                "anchor_rent_free_concession": anchor["rent_free_concession"],
                "non_anchor_rent_free_concession": non_anchor["rent_free_concession"],
                "rent_free_concession": rent_free_concession,
                "anchor_billed_rent": anchor["billed_rent"],
                "non_anchor_billed_rent": non_anchor["billed_rent"],
                "billed_rent": billed_rent,
                "collection_loss": collection_loss,
                "collected_rent": collected_rent,
                "other_income": other_income,
                "effective_property_revenue": effective_property_revenue,
                "fixed_operating_expense": fixed_operating_expense,
                "variable_operating_expense": variable_operating_expense,
                "property_operating_expense": property_operating_expense,
                "property_noi": property_noi,
                "annualized_property_noi": property_noi * 12,
            }
        )

    ledger = pd.DataFrame(rows)
    underwriting_start = config.underwriting_month - config.underwriting_lookback_months + 1
    underwriting_rows = ledger[
        ledger["month"].between(underwriting_start, config.underwriting_month)
    ]
    underwritten_monthly_noi = float(underwriting_rows["property_noi"].mean())
    positive_noi = ledger.loc[ledger["property_noi"] > 0, "month"]
    first_positive_noi_month = int(positive_noi.iloc[0]) if not positive_noi.empty else None

    result = OperatingLedgerResult(
        ledger=ledger,
        underwriting_month=config.underwriting_month,
        underwritten_monthly_noi=underwritten_monthly_noi,
        underwritten_annual_noi=underwritten_monthly_noi * 12,
        first_positive_noi_month=first_positive_noi_month,
    )
    validate_operating_ledger(result, config)
    return result


def _assert_close(
    actual: pd.Series,
    expected: pd.Series,
    *,
    tolerance: float,
    label: str,
) -> None:
    differences = (actual - expected).abs()
    if bool((differences > tolerance).any()):
        row_index = int(differences.idxmax())
        raise OperatingLedgerInvariantError(f"{label} does not reconcile at row {row_index}")


def validate_operating_ledger(
    result: OperatingLedgerResult,
    config: OperatingLedgerConfig,
) -> None:
    """Validate the bottom-up rent, revenue, expense, and NOI contract."""

    ledger = result.ledger
    tolerance = config.amount_tolerance
    expected_months = list(range(config.operations_start_month, config.operations_end_month + 1))
    if ledger["month"].tolist() != expected_months:
        raise OperatingLedgerInvariantError("operating ledger months are incomplete")

    occupancy_columns = [
        "anchor_occupancy",
        "non_anchor_occupancy",
        "physical_occupancy",
    ]
    if bool(
        ((ledger[occupancy_columns] < -tolerance) | (ledger[occupancy_columns] > 1 + tolerance))
        .any()
        .any()
    ):
        raise OperatingLedgerInvariantError("occupancy must remain between zero and one")

    _assert_close(
        ledger["gross_potential_rent"],
        (ledger["anchor_gross_potential_rent"] + ledger["non_anchor_gross_potential_rent"]),
        tolerance=tolerance,
        label="gross potential rent",
    )
    _assert_close(
        ledger["occupied_rent"],
        ledger["anchor_occupied_rent"] + ledger["non_anchor_occupied_rent"],
        tolerance=tolerance,
        label="occupied rent",
    )
    _assert_close(
        ledger["billed_rent"],
        ledger["occupied_rent"] - ledger["rent_free_concession"],
        tolerance=tolerance,
        label="billed rent",
    )
    _assert_close(
        ledger["collected_rent"],
        ledger["billed_rent"] - ledger["collection_loss"],
        tolerance=tolerance,
        label="collected rent",
    )
    _assert_close(
        ledger["effective_property_revenue"],
        ledger["collected_rent"] + ledger["other_income"],
        tolerance=tolerance,
        label="effective property revenue",
    )
    _assert_close(
        ledger["property_operating_expense"],
        ledger["fixed_operating_expense"] + ledger["variable_operating_expense"],
        tolerance=tolerance,
        label="property operating expense",
    )
    _assert_close(
        ledger["property_noi"],
        ledger["effective_property_revenue"] - ledger["property_operating_expense"],
        tolerance=tolerance,
        label="property NOI",
    )

    underwriting_start = config.underwriting_month - config.underwriting_lookback_months + 1
    expected_underwritten_noi = float(
        ledger.loc[
            ledger["month"].between(underwriting_start, config.underwriting_month),
            "property_noi",
        ].mean()
    )
    if not math.isclose(
        result.underwritten_monthly_noi,
        expected_underwritten_noi,
        abs_tol=tolerance,
    ):
        raise OperatingLedgerInvariantError("underwritten NOI does not match its lookback")
