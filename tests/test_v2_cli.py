import json

import pandas as pd
from typer.testing import CliRunner

from pf_liquidity_risk.modeling.v2.cli import app

runner = CliRunner()


def test_base_command_prints_summary_and_writes_ledger(tmp_path):
    output = tmp_path / "ledgers" / "base.csv"

    result = runner.invoke(app, ["base", "--ledger-output", str(output)])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "exit"
    assert payload["refinance_binding_constraint"] == "ltv"
    assert output.exists()
    ledger = pd.read_csv(output)
    assert ledger.iloc[-1]["closing_cash"] == 0


def test_simulate_command_is_seeded_and_writes_scenarios(tmp_path):
    output = tmp_path / "scenarios.csv"

    result = runner.invoke(
        app,
        ["simulate", "--iterations", "20", "--seed", "7", "--output", str(output)],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["iterations"] == 20
    assert payload["seed"] == 7
    assert 0 <= payload["refi_success_rate"] <= 1
    scenarios = pd.read_csv(output)
    assert len(scenarios) == 20
    assert scenarios["scenario_id"].is_unique
