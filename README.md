# Liquidity Risk in Highly Leveraged Real Estate PF

## Stochastic Cash Flow Modeling & Monte Carlo Risk Analysis (₩24.6B GDV)

[![CCDS Project template](https://img.shields.io/badge/CCDS-Project%20template-328F97?logo=cookiecutter)](https://cookiecutter-data-science.drivendata.org/)

This repository presents a **stochastic liquidity risk analysis** for a highly leveraged real estate development project (₩24.6B GDV). It applies Monte Carlo simulation methods to quantify structural weaknesses in project finance (PF) capital structures and support data-driven investment decisions.

---

## 📌 Executive Summary

The project involves a commercial parking tower development facing significant liquidity risk due to aggressive gearing (77% initial LTV) and a critical 14-month timing gap between asset completion and demand activation. By leveraging **30,000-iteration Monte Carlo simulations** with triangular probability distributions, this analysis quantifies default probability, refinancing viability, and equity IRR distributions.

> **Key Finding:** Under base-case assumptions, the project exhibits a **~35% probability of failure** (default or refinancing failure) before exit, driven primarily by interest capitalization and the NOI ramp-up period.

---

## 1. Transaction Overview – Capital Stack

| Category | Value (KRW) | % of Total | Notes |
| :--- | :--- | :--- | :--- |
| **Initial Equity** | ₩5.6B | 23% | Committed sponsor capital |
| **Senior Loan** | ₩19.0B | 77% | Construction + Bridge financing |
| **Total Project Cost** | ₩24.6B | 100% | Equity + Senior debt |
| **Initial LTV** | **77%** | — | Debt / (Debt + Equity) |
| **Target GDV** | ~₩30B – ₩35B | — | Stabilized asset value (Cap Rate 5.5%) |
| **Leverage Ratio** | **3.4x** | — | Debt / Equity multiple |

---

## 2. Core Investment Issue: The 24-Month Structural Gap

A critical **timing mismatch** exists between three project phases:

* **Phase 1: Construction (0–16 months)** – Zero revenue, 100% interest capitalization
* **Phase 2: Stabilization (16–24 months)** – Ramp-up period, partial revenue (₩50M–₩150M/month)
* **Phase 3: Post-Opening (24–36 months)** – Stabilized operations (₩120M–₩250M/month)

During Phase 2, the project experiences **Negative Carry** where debt service outpaces NOI. Additionally, construction delays (stochastically modeled 0–6 months) directly erode equity buffers.

---

## 3. Analytical Approach & Methodology

### 3.1 Stochastic Modeling Framework

I developed a **Python-based Monte Carlo simulation engine** to evaluate liquidity risk across 30,000 randomized scenarios.

**Key Stochastic Variables (Triangular Distributions):**

| Variable | Min | Mode | Max | Phase |
| :--- | :--- | :--- | :--- | :--- |
| Interest Rate | 10% | 14% | 18% | Pre-Completion |
| Interest Rate | 8% | 11% | 14% | Stabilization |
| Interest Rate | 5% | 7% | 9% | Post-Court Opening |
| Monthly Revenue | ₩50M | ₩120M | ₩150M | Stabilization |
| Monthly Revenue | ₩120M | ₩200M | ₩250M | Post-Opening |
| Construction Delay | 0 mo | 2 mo | 6 mo | One-time shock |
| Refinancing LTV | 70% | 80% | 85% | Month 24 |

### 3.2 Simulation Logic
```python
# Each iteration simulates 36 months of:
# 1. Phase-dependent revenue generation
# 2. Interest accrual (with phase-specific capitalization ratios)
# 3. Cash sweep debt paydown (when NOI > 0)
# 4. Equity buffer erosion under negative carry
# 5. Refinancing viability check (Month 24)
# 6. Exit valuation via Income Approach (Cap Rate 5.5%)
```

**Critical Checkpoints:**

* **Insolvency Check:** Triggered when equity ≤ 0 → Immediate default
* **Refinancing Check (Month 24):** Debt must be ≤ (Property Value × LTV) or refinancing fails
* **Exit Transaction (Month 36):** Final equity = Property Value – Remaining Debt – Exit Costs (1–2%)

### 3.3 Interest Capitalization Structure

| Phase | Capitalization Ratio | Economic Rationale |
| :--- | :--- | :--- |
| Construction | 100% | No cash flow to service debt |
| Stabilization | 40% | Partial NOI covers ~60% of interest |
| Exit | 0% | Fully amortizing debt service |

---

## 4. Key Findings & Risk Metrics

### 4.1 Outcome Probability Distribution

Based on 30,000 simulations:

| Outcome | Probability | Description |
| :--- | :--- | :--- |
| **Successful Exit** | ~65% | Project survives to Month 36 with positive equity |
| **Default** | ~25% | Equity wipeout before Month 24 |
| **Refinancing Failure** | ~10% | Debt exceeds LTV limit at Month 24 |

### 4.2 Risk Metrics

* **95% Capital at Risk (VaR):** ₩4.2B (~75% of initial equity)
* **Expected Loss:** ₩1.8B (32% of equity base)
* **Median IRR (Exit Cases):** 8.5% annualized
* **IRR Volatility:** 6.2% standard deviation

### 4.3 Survival Rate Dynamics

The simulation tracks **cumulative survival probability** month-by-month:

* **Month 16 (Completion):** 88% survival rate (construction delays cause early defaults)
* **Month 18–22:** Steepest decline (negative carry period)
* **Month 24 (Refinancing Gate):** 72% survival rate
* **Month 36 (Exit):** 65% success rate

---

## 5. Strategic Recommendations

### 5.1 Pre-Construction Phase

1. **Equity Cushion Sizing:** Increase equity to ₩7B–₩8B to absorb 6-month construction delays
2. **Interest Rate Hedging:** Fix construction-phase rate at ≤12% to reduce tail risk

### 5.2 Stabilization Phase (Months 16–24)

1. **Aggressive Lease-Up:** Incentivize early occupancy to accelerate NOI breakeven
2. **Mezzanine Capital:** Secure ₩2B–₩3B subordinated facility to bridge liquidity gap
3. **Partial Asset Sale:** Pre-sell 20–30% of units to deleverage before refinancing checkpoint

### 5.3 Refinancing Strategy (Month 24)

1. **Conservative LTV Target:** Aim for 70% LTV to ensure refinancing approval under stress
2. **Rolling NOI Documentation:** Maintain 6-month trailing NOI ≥ ₩180M/month for valuation confidence

---

## 6. Project Organization (CCDS Structure)

This project follows the **Cookiecutter Data Science** standard for modularity and reproducibility.
```text
├── README.md          <- Project overview (this file)
├── data
│   ├── raw            <- Market comparables, interest rate data
│   └── processed      <- Cleaned inputs for simulation
├── notebooks          <- Jupyter notebooks for sensitivity analysis
├── reports            <- Generated analysis reports
│   └── figures        <- Monte Carlo output visualizations
│       └── pf_liquidity_analysis_v1.png
├── requirements.txt   <- Python environment (numpy, pandas, matplotlib)
└── pf_liquidity_risk  <- Source code for simulation
    ├── config.py       <- Project parameters (FIGURES_DIR, constants)
    ├── modeling
    │   └── train.py    <- Monte Carlo simulation engine
    └── plots.py        <- Visualization functions
```

---

## 7. Technical Implementation

### 7.1 Core Modules

**`PFConfig` (Data Class)**
* Encapsulates all financial parameters and probability distributions
* Supports scenario testing by modifying initialization parameters

**`PFInvestmentModel` (Simulation Engine)**
* Generates single stochastic path (36 months)
* Returns status: `exit`, `default`, `refi_fail`, or `survived_no_exit`

**`run_simulation()` Function**
* Executes 30,000 Monte Carlo iterations
* Returns pandas DataFrame with results + configuration object

**`plot_enhanced_results()` Function**
* Generates 3-panel analytical dashboard:
  1. Outcome distribution (bar chart)
  2. IRR distribution histogram (exit cases only)
  3. Survival rate curve (monthly tracking)

### 7.2 Running the Analysis
```bash
# Install dependencies
pip install -r requirements.txt

# Execute simulation
python pf_liquidity_risk/modeling/train.py

# Output:
# - Console: Risk metrics (VaR, probabilities, IRR statistics)
# - File: reports/figures/pf_liquidity_analysis_v1.png
```

---

## 8. Skills & Tools

* **Domain Expertise:** Real Estate Project Finance, Structured Finance, Risk Management
* **Quantitative Methods:** Monte Carlo Simulation, Stochastic Modeling, Capital Structure Optimization
* **Technical Stack:** Python (NumPy, Pandas, Matplotlib), Statistical Distributions, Cash Flow Modeling
* **Engineering:** Modular code design (CCDS), reproducible research, data visualization

---

## 9. Key Takeaway

In highly leveraged real estate development, **liquidity risk dominates market risk** when structural mismatches exist between debt terms and NOI stabilization. By quantifying downside scenarios through stochastic simulation, sponsors can:

1. **Right-size equity commitments** to absorb construction delays
2. **Structure refinancing covenants** around realistic NOI ramp-up profiles
3. **Identify optimal exit timing** to maximize risk-adjusted returns

This framework transforms qualitative "what-if" discussions into **quantified probability distributions**, enabling data-driven capital allocation decisions.

---

## 10. Future Enhancements

- [ ] Add correlation structures between interest rates and revenue (e.g., rising rates → lower demand)
- [ ] Implement waterfall cash flow logic for mezzanine/equity tranches
- [ ] Develop interactive dashboard (Plotly/Streamlit) for live scenario testing
- [ ] Integrate macroeconomic scenarios (recession, rate shock, market correction)
- [ ] Add Value at Risk (VaR) and Conditional VaR (CVaR) analytics

---

**Repository:** [GitHub - PF Liquidity Risk Analysis](https://github.com/yourusername/pf-liquidity-risk)  
**Author:** [Your Name]  
**License:** MIT

---