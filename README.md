# PF Risk Simulator

[![CI](https://github.com/aestim/pf-risk-simulator/actions/workflows/ci.yml/badge.svg)](https://github.com/aestim/pf-risk-simulator/actions/workflows/ci.yml)
[![Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://real-estate-pf-liquidity-risk.streamlit.app/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A monthly cash-flow and refinancing stress test for Korean real estate project finance.

```text
Land purchase → Bridge loan → Main PF → Construction and lease-up
→ Refinancing → Normal sale or distressed exit
```

The model answers one practical question:

> Can the completed property raise enough take-out debt to repay its construction loans?

It connects development costs, debt draws, leasing, NOI, refinancing, and sale proceeds
in one monthly ledger. Monte Carlo scenarios then stress costs, delays, rent, occupancy,
interest rates, and exit value together.

> This is an educational project built with synthetic assumptions. It is not a market
> forecast or a tool for real investment and lending decisions.

## Quick start

### Live demo

[Open the Streamlit demo](https://real-estate-pf-liquidity-risk.streamlit.app/)

The hosted demo currently runs the legacy V1 model. The Korean deal-based V2 model is
available locally.

### Run the V2 dashboard

Python 3.10 is required.

```bash
git clone https://github.com/aestim/pf-risk-simulator.git
cd pf-risk-simulator

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

streamlit run pf_liquidity_risk/v2_app.py
```

On Windows, activate the environment with `venv\Scripts\activate`.

The dashboard has three steps:

1. Choose a base, conservative, or optimistic case.
2. Check the refinancing result and the funding gap.
3. Open the cash-flow or scenario tabs only when more detail is needed.

## What V2 models

| Stage | Included logic |
| --- | --- |
| Development | Land, construction costs, bridge debt, and main-PF draws |
| Operations | Lease-up, rent-free periods, collection loss, OPEX, and monthly NOI |
| Refinancing | The lowest limit from LTV, Debt Yield, DSCR, and lender commitment |
| Recovery | Sponsor cure, one extension, and distressed sale |
| Exit | Debt repayment, equity waterfall, and sponsor IRR |
| Stress test | Correlated shocks to cost, delay, leasing, rates, LTV, and cap rate |

The central check is:

```text
Take-out capacity >= New debt required to repay the existing PF loans
```

## Command line

```bash
# Deterministic base case
python -m pf_liquidity_risk.modeling.v2 base

# Base case with a monthly ledger
python -m pf_liquidity_risk.modeling.v2 base \
  --ledger-output reports/v2_base_ledger.csv

# 1,000 seeded stress scenarios
python -m pf_liquidity_risk.modeling.v2 simulate \
  --iterations 1000 --seed 42 \
  --output reports/v2_scenarios.csv
```

## Data pipeline

The legacy V1 engine also has a reproducible analytics pipeline:

```text
Rate extraction → Validation → Calibration → Simulation
→ DuckDB load → dbt marts
```

```bash
# Run offline without an API key
python -m pipeline.cli run --offline --iterations 1000

# Query the output mart
python -m pipeline.cli query \
  "SELECT status, pct FROM mart_outcome_summary ORDER BY pct DESC"
```

## Repository map

```text
pf_liquidity_risk/v2_app.py        Beginner-friendly V2 dashboard
pf_liquidity_risk/modeling/v2/     Monthly PF engine and stress scenarios
pipeline/                           Rate and simulation data pipeline
dbt/                                DuckDB models and data tests
tests/                              Model, pipeline, CLI, and dashboard tests
docs/                               V2 deal rules and architecture
```

## Verification

```bash
ruff format --check
ruff check
pytest -q
python -m pipeline.cli run --offline --iterations 1000
```

The same checks run in GitHub Actions.

## Documentation

- [V2 deal contract and assumptions](docs/v2-deal-contract.md)
- [V2 architecture](docs/v2-architecture.md)
- [Study checklist](STUDY_PLAN.md)

V1 remains in the repository for reproducibility. New model and dashboard work should
use V2.

## License

[MIT License](LICENSE) · Minsung Kim
