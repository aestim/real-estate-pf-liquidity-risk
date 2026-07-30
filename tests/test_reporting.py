import pandas as pd
import pytest

from pf_liquidity_risk.reporting import equity_loss_metrics


def test_equity_loss_metrics_use_saved_run_equity_basis():
    df = pd.DataFrame({"final_equity": [0.0, 50.0, 150.0]})

    metrics = equity_loss_metrics(df, initial_equity=100.0)

    assert metrics["expected_loss_pct"] == pytest.approx(33.333333)
    assert metrics["var_95_pct"] == pytest.approx(95.0)


def test_equity_loss_metrics_reject_invalid_inputs():
    with pytest.raises(ValueError, match="positive"):
        equity_loss_metrics(pd.DataFrame({"final_equity": [0.0]}), initial_equity=0)
    with pytest.raises(ValueError, match="final_equity"):
        equity_loss_metrics(pd.DataFrame({"status": ["exit"]}), initial_equity=100)
