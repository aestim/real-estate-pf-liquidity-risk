"""
Tests for the data pipeline. All run fully offline (committed sample data),
so they are deterministic and need no network or secrets in CI.
"""

import duckdb

from pipeline import calibrate as calibrate_stage
from pipeline import config, extract_rates
from pipeline import load as load_stage
from pipeline import simulate as simulate_stage
from pipeline import transform as transform_stage


def test_extract_offline_returns_clean_frame():
    df = extract_rates.extract(offline=True)
    assert not df.empty
    assert list(df.columns) == ["date", "rate_pct"]
    assert df["rate_pct"].notna().all()
    assert config.RATES_RAW_CSV.exists()


def test_calibrate_produces_ordered_triangles():
    rates = extract_rates.extract(offline=True)
    params = calibrate_stage.calibrate(rates)
    for key in ("pre_refi_rate", "post_refi_rate"):
        lo, mode, hi = params[key]
        assert lo <= mode <= hi
        assert lo > 0


def test_full_pipeline_offline_builds_warehouse():
    extract_rates.extract(offline=True)
    calibrate_stage.calibrate()
    simulate_stage.simulate(iterations=800, seed=1)
    load_stage.load()
    counts = transform_stage.transform()

    assert counts["mart_outcome_summary"] >= 1
    assert counts["mart_survival_curve"] == 36

    con = duckdb.connect(str(config.DUCKDB_PATH), read_only=True)
    try:
        facts = con.execute("SELECT COUNT(*) FROM fact_scenario").fetchone()[0]
        assert facts == 800

        # outcome percentages must sum to ~100 within each batch
        total_pct = con.execute("SELECT SUM(pct) FROM mart_outcome_summary").fetchone()[0]
        assert abs(total_pct - 100.0) < 0.5

        # survival rate is monotonic non-increasing
        rates = [
            r[0]
            for r in con.execute(
                "SELECT survival_rate FROM mart_survival_curve ORDER BY month"
            ).fetchall()
        ]
        assert all(a >= b - 1e-9 for a, b in zip(rates, rates[1:]))
    finally:
        con.close()
