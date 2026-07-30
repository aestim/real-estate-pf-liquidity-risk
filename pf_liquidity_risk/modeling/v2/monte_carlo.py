"""Regime-correlated Monte Carlo wrapper around the deterministic V2 engine."""

from dataclasses import dataclass, replace
import math

import numpy as np
import pandas as pd

from pf_liquidity_risk.modeling.v2.project import (
    ProjectV2Config,
    build_base_project_config,
    run_project,
)


@dataclass(frozen=True)
class MacroRegime:
    """Ranges sampled together to preserve directional macro correlation."""

    name: str
    probability: float
    hard_cost_overrun_range: tuple[float, float]
    delay_month_range: tuple[int, int]
    rent_factor_range: tuple[float, float]
    stabilized_occupancy_range: tuple[float, float]
    lease_up_month_range: tuple[int, int]
    collection_loss_range: tuple[float, float]
    interest_rate_shock_range: tuple[float, float]
    cap_rate_shock_range: tuple[float, float]
    maximum_ltv_range: tuple[float, float]


@dataclass(frozen=True)
class ScenarioDraw:
    """One fully materialized set of scenario shocks."""

    regime: str
    hard_cost_overrun: float
    delay_months: int
    rent_factor: float
    stabilized_occupancy: float
    lease_up_months: int
    collection_loss_rate: float
    interest_rate_shock: float
    cap_rate_shock: float
    maximum_ltv: float


REGIMES: tuple[MacroRegime, ...] = (
    MacroRegime(
        name="normal",
        probability=0.60,
        hard_cost_overrun_range=(0.00, 0.04),
        delay_month_range=(0, 1),
        rent_factor_range=(0.98, 1.05),
        stabilized_occupancy_range=(0.92, 0.97),
        lease_up_month_range=(10, 13),
        collection_loss_range=(0.005, 0.015),
        interest_rate_shock_range=(-0.005, 0.005),
        cap_rate_shock_range=(-0.0025, 0.0025),
        maximum_ltv_range=(0.63, 0.68),
    ),
    MacroRegime(
        name="stress",
        probability=0.30,
        hard_cost_overrun_range=(0.03, 0.08),
        delay_month_range=(1, 3),
        rent_factor_range=(0.88, 0.98),
        stabilized_occupancy_range=(0.82, 0.92),
        lease_up_month_range=(13, 18),
        collection_loss_range=(0.015, 0.04),
        interest_rate_shock_range=(0.005, 0.02),
        cap_rate_shock_range=(0.0025, 0.01),
        maximum_ltv_range=(0.58, 0.64),
    ),
    MacroRegime(
        name="severe",
        probability=0.10,
        hard_cost_overrun_range=(0.07, 0.10),
        delay_month_range=(3, 6),
        rent_factor_range=(0.72, 0.90),
        stabilized_occupancy_range=(0.65, 0.85),
        lease_up_month_range=(18, 24),
        collection_loss_range=(0.04, 0.08),
        interest_rate_shock_range=(0.02, 0.04),
        cap_rate_shock_range=(0.01, 0.025),
        maximum_ltv_range=(0.50, 0.60),
    ),
)


def _validate_regimes(regimes: tuple[MacroRegime, ...]) -> None:
    if not regimes:
        raise ValueError("at least one macro regime is required")
    if not math.isclose(sum(item.probability for item in regimes), 1.0, abs_tol=1e-12):
        raise ValueError("macro regime probabilities must sum to one")
    if any(item.probability <= 0 for item in regimes):
        raise ValueError("macro regime probabilities must be positive")


def smooth_cost_weights(months: int) -> tuple[float, ...]:
    """Return a simple bell-shaped construction draw curve."""

    if months <= 0:
        raise ValueError("months must be positive")
    raw = np.array(
        [(index + 1) * (months - index) for index in range(months)],
        dtype=float,
    )
    return tuple((raw / raw.sum()).tolist())


def sample_scenario(
    rng: np.random.Generator,
    regimes: tuple[MacroRegime, ...] = REGIMES,
) -> ScenarioDraw:
    """Sample one regime, then conditionally sample all correlated shocks."""

    _validate_regimes(regimes)
    probabilities = [item.probability for item in regimes]
    regime = regimes[int(rng.choice(len(regimes), p=probabilities))]
    return ScenarioDraw(
        regime=regime.name,
        hard_cost_overrun=float(rng.uniform(*regime.hard_cost_overrun_range)),
        delay_months=int(
            rng.integers(
                regime.delay_month_range[0],
                regime.delay_month_range[1] + 1,
            )
        ),
        rent_factor=float(rng.uniform(*regime.rent_factor_range)),
        stabilized_occupancy=float(rng.uniform(*regime.stabilized_occupancy_range)),
        lease_up_months=int(
            rng.integers(
                regime.lease_up_month_range[0],
                regime.lease_up_month_range[1] + 1,
            )
        ),
        collection_loss_rate=float(rng.uniform(*regime.collection_loss_range)),
        interest_rate_shock=float(rng.uniform(*regime.interest_rate_shock_range)),
        cap_rate_shock=float(rng.uniform(*regime.cap_rate_shock_range)),
        maximum_ltv=float(rng.uniform(*regime.maximum_ltv_range)),
    )


def build_scenario_config(
    draw: ScenarioDraw,
    base: ProjectV2Config | None = None,
) -> ProjectV2Config:
    """Apply one scenario draw without changing the total base budget."""

    base = base or build_base_project_config()
    hard_cost_increase = base.development.uses.hard_cost * draw.hard_cost_overrun
    if hard_cost_increase > base.development.uses.contingency + 1e-8:
        raise ValueError("hard-cost shock exceeds the modeled contingency")

    uses = replace(
        base.development.uses,
        hard_cost=base.development.uses.hard_cost + hard_cost_increase,
        contingency=base.development.uses.contingency - hard_cost_increase,
    )
    sources = replace(
        base.development.sources,
        additional_sponsor_equity_commitment=50.0,
    )
    timeline = replace(
        base.development.timeline,
        completion_month=(base.development.timeline.completion_month + draw.delay_months),
    )
    financing = replace(
        base.development.financing,
        bridge_annual_rate=max(
            0.001,
            base.development.financing.bridge_annual_rate + draw.interest_rate_shock,
        ),
        senior_pf_annual_rate=max(
            0.001,
            base.development.financing.senior_pf_annual_rate + draw.interest_rate_shock,
        ),
        subordinate_annual_rate=max(
            0.001,
            base.development.financing.subordinate_annual_rate + draw.interest_rate_shock,
        ),
    )
    development = replace(
        base.development,
        uses=uses,
        sources=sources,
        timeline=timeline,
        financing=financing,
        hard_cost_weights=smooth_cost_weights(len(timeline.construction_months)),
    )

    operating_start = timeline.completion_month + 1
    operating = replace(
        base.operating,
        operations_start_month=operating_start,
        underwriting_month=operating_start + 11,
        operations_end_month=base.operating.operations_end_month + draw.delay_months,
        anchor=replace(
            base.operating.anchor,
            monthly_base_rent_per_area=(
                base.operating.anchor.monthly_base_rent_per_area * draw.rent_factor
            ),
        ),
        non_anchor=replace(
            base.operating.non_anchor,
            monthly_base_rent_per_area=(
                base.operating.non_anchor.monthly_base_rent_per_area * draw.rent_factor
            ),
            stabilized_occupancy=draw.stabilized_occupancy,
            lease_up_months=draw.lease_up_months,
        ),
        collection_loss_rate=draw.collection_loss_rate,
    )
    takeout = replace(
        base.takeout,
        capitalization_rate=base.takeout.capitalization_rate + draw.cap_rate_shock,
        maximum_ltv=draw.maximum_ltv,
        annual_interest_rate=(base.takeout.annual_interest_rate + draw.interest_rate_shock),
    )
    sale = replace(
        base.sale,
        exit_capitalization_rate=(base.sale.exit_capitalization_rate + draw.cap_rate_shock),
    )
    return ProjectV2Config(
        development=development,
        operating=operating,
        takeout=takeout,
        sale=sale,
        resolution=base.resolution,
    )


def _result_row(
    *,
    scenario_id: int,
    draw: ScenarioDraw,
    config: ProjectV2Config,
) -> dict[str, float | int | str | bool]:
    result = run_project(config)
    final_attempt = result.refinance_attempts[-1] if result.refinance_attempts else None
    first_attempt = result.refinance_attempts[0] if result.refinance_attempts else None
    sale = result.sale
    sponsor_loss = max(
        0.0,
        result.sponsor_equity_invested - result.sponsor_distribution,
    )
    return {
        "scenario_id": scenario_id,
        "regime": draw.regime,
        "status": result.status,
        "terminal_month": result.terminal_month,
        "hard_cost_overrun": draw.hard_cost_overrun,
        "delay_months": draw.delay_months,
        "rent_factor": draw.rent_factor,
        "stabilized_occupancy": draw.stabilized_occupancy,
        "lease_up_months": draw.lease_up_months,
        "collection_loss_rate": draw.collection_loss_rate,
        "interest_rate_shock": draw.interest_rate_shock,
        "cap_rate_shock": draw.cap_rate_shock,
        "maximum_ltv": draw.maximum_ltv,
        "refi_attempts": len(result.refinance_attempts),
        "refi_succeeded": any(
            attempt.status != "refi_shortfall" for attempt in result.refinance_attempts
        ),
        "extension_used": bool((result.ledger["event"] == "refi_shortfall_extension").any()),
        "first_refi_capacity": (first_attempt.capacity.gross_capacity if first_attempt else 0.0),
        "final_refi_capacity": (final_attempt.capacity.gross_capacity if final_attempt else 0.0),
        "refi_funding_gap": result.refi_funding_gap,
        "sponsor_equity_invested": result.sponsor_equity_invested,
        "sponsor_distribution": result.sponsor_distribution,
        "sponsor_loss": sponsor_loss,
        "sponsor_loss_pct": (
            sponsor_loss / result.sponsor_equity_invested
            if result.sponsor_equity_invested > 0
            else 0.0
        ),
        "sponsor_irr": result.sponsor_irr,
        "combined_equity_irr": result.combined_equity_irr,
        "sponsor_equity_multiple": result.sponsor_equity_multiple,
        "combined_equity_multiple": result.combined_equity_multiple,
        "sale_value": sale.gross_sale_proceeds if sale else 0.0,
        "lender_shortfall": result.lender_shortfall,
    }


def run_v2_monte_carlo(
    iterations: int = 1_000,
    seed: int = 42,
    regimes: tuple[MacroRegime, ...] = REGIMES,
    base: ProjectV2Config | None = None,
) -> pd.DataFrame:
    """Run reproducible V2 scenario paths.

    Regime probabilities and conditional ranges are synthetic stress weights,
    not estimated frequencies of the Korean PF market.
    """

    if iterations <= 0:
        raise ValueError("iterations must be positive")
    _validate_regimes(regimes)
    rng = np.random.default_rng(seed)
    rows = []
    for scenario_id in range(iterations):
        draw = sample_scenario(rng, regimes)
        rows.append(
            _result_row(
                scenario_id=scenario_id,
                draw=draw,
                config=build_scenario_config(draw, base=base),
            )
        )
    return pd.DataFrame(rows)


def summarize_v2_results(results: pd.DataFrame) -> dict[str, float]:
    """Return compact scenario frequencies and loss/return metrics."""

    required = {
        "status",
        "refi_succeeded",
        "extension_used",
        "sponsor_irr",
        "sponsor_loss_pct",
        "sponsor_equity_invested",
        "sponsor_distribution",
    }
    missing = required.difference(results.columns)
    if missing:
        raise ValueError(f"missing V2 result columns: {sorted(missing)}")
    if results.empty:
        raise ValueError("results cannot be empty")

    successful_exits = results[results["status"].isin(["exit", "exit_after_extension"])]
    distressed = results["status"].str.contains(
        "distressed|default",
        case=False,
        regex=True,
    )
    total_invested = float(results["sponsor_equity_invested"].sum())
    total_distributed = float(results["sponsor_distribution"].sum())
    portfolio_loss = max(0.0, total_invested - total_distributed)
    return {
        "refi_success_rate": float(results["refi_succeeded"].mean()),
        "extension_rate": float(results["extension_used"].mean()),
        "distressed_or_default_rate": float(distressed.mean()),
        "successful_exit_rate": float(
            results["status"].isin(["exit", "exit_after_extension"]).mean()
        ),
        "median_sponsor_irr_success": (
            float(successful_exits["sponsor_irr"].median()) if not successful_exits.empty else -1.0
        ),
        "mean_sponsor_loss_pct": float(results["sponsor_loss_pct"].mean()),
        "portfolio_sponsor_loss_pct": (
            portfolio_loss / total_invested if total_invested > 0 else 0.0
        ),
    }
