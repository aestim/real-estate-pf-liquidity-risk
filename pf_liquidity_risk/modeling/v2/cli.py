"""Command-line interface for the contract-driven V2 model."""

import json
from pathlib import Path
from typing import Any

import pandas as pd
import typer

from pf_liquidity_risk.modeling.v2.monte_carlo import (
    run_v2_monte_carlo,
    summarize_v2_results,
)
from pf_liquidity_risk.modeling.v2.project import run_project

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Run the synthetic Korean rental-PF V2 model.",
)


def _write_csv(frame: pd.DataFrame, output: Path | None) -> None:
    if output is None:
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output, index=False)


def _print_json(payload: dict[str, Any]) -> None:
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))


@app.command("base")
def base_case(
    ledger_output: Path | None = typer.Option(
        None,
        "--ledger-output",
        help="Optional path for the monthly integrated ledger CSV.",
    ),
) -> None:
    """Run the deterministic V2 base case."""

    result = run_project()
    first_refi = result.refinance_attempts[0] if result.refinance_attempts else None
    sale = result.sale
    payload = {
        "status": result.status,
        "terminal_month": result.terminal_month,
        "refinance_status": first_refi.status if first_refi else None,
        "refinance_binding_constraint": (
            first_refi.capacity.binding_constraint if first_refi else None
        ),
        "refinance_gross_capacity": (first_refi.capacity.gross_capacity if first_refi else 0.0),
        "sponsor_equity_invested": result.sponsor_equity_invested,
        "sponsor_distribution": result.sponsor_distribution,
        "sponsor_irr": result.sponsor_irr,
        "sponsor_equity_multiple": result.sponsor_equity_multiple,
        "combined_equity_irr": result.combined_equity_irr,
        "gross_sale_proceeds": sale.gross_sale_proceeds if sale else 0.0,
        "lender_shortfall": result.lender_shortfall,
        "assumption_notice": "Synthetic case; not a forecast or observed market frequency.",
    }
    _write_csv(result.ledger, ledger_output)
    _print_json(payload)


@app.command("simulate")
def simulate(
    iterations: int = typer.Option(
        1_000,
        "--iterations",
        "-n",
        min=1,
        help="Number of scenario paths.",
    ),
    seed: int = typer.Option(42, "--seed", help="Random seed."),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Optional path for scenario-level CSV results.",
    ),
) -> None:
    """Run regime-correlated V2 Monte Carlo scenarios."""

    results = run_v2_monte_carlo(iterations=iterations, seed=seed)
    _write_csv(results, output)
    summary: dict[str, Any] = {
        "iterations": iterations,
        "seed": seed,
        **summarize_v2_results(results),
        "assumption_notice": (
            "Regime weights and conditional ranges are synthetic stress assumptions, "
            "not estimated Korean PF probabilities."
        ),
    }
    _print_json(summary)


def main() -> None:
    """Run the Typer application."""

    app()


if __name__ == "__main__":
    main()
