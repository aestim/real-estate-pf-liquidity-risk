# Liquidity Risk in Highly Leveraged Real Estate PF

## Cash Flow Stress Testing & Capital Structure Analysis (£12.7M GDV)

[![CCDS Project template](https://img.shields.io/badge/CCDS-Project%20template-328F97?logo=cookiecutter)](https://cookiecutter-data-science.drivendata.org/)

This repository presents a **quantitative liquidity risk analysis** for a highly leveraged real estate development project ($20M+ GDV). It applies informatics-based financial modelling to identify structural weaknesses in project finance (PF) and support data-driven capital structure decisions.

---

## 📌 Executive Summary

The project involves a commercial parking tower development facing a significant funding gap and liquidity risk due to aggressive gearing and a timing mismatch in regional infrastructure. By leveraging **Monte Carlo simulations**, this analysis quantifies the probability of equity wipeout and provides a strategic roadmap for de-risking the capital stack.

> **Currency Note:** All GBP figures are indicative conversions from KRW using an approximate spot rate (**£1 ≈ ₩1,970**) for analytical consistency. All core modelling and assumptions are performed in KRW.

---

## 1. Transaction Overview – Capital Stack

| Category | Value (KRW) | Value (GBP) | Notes |
| :--- | :--- | :--- | :--- |
| **Appraisal Value** | ₩19.0B | ~£9.65M | Current asset valuation |
| **Equity Capital** | ₩5.7B | ~£2.90M | ~23% of total project cost |
| **Target Debt (PF)** | ₩19B – ₩23B | ~£9.65M – £11.69M | Senior / Mezzanine financing |
| **Implied LTV** | **100% – 121%** | **100% – 121%** | **Primary structural risk** |
| **Debt / Equity Multiple** | ~3.3x – 4.0x | ~3.3x – 4.0x | High leverage profile |
| **Gross Development Value** | ~₩25.0B | ~£12.70M | Stabilised value assumption |

---

## 2. Core Investment Issue: The 14-Month Structural Gap

A critical **14-month timing mismatch** exists between asset completion and the activation of the primary demand driver:

* **Asset Completion:** January 2027
* **District Court Opening:** March 2028

During this period, the project experiences a **Negative Carry** profile where high-cost debt accrual outpaces Net Operating Income (NOI). Liquidity risk is driven not by asset quality, but by **capital structure and timing misalignment.**

---

## 3. Analytical Approach & Methodology

I developed a **Python-based cash flow simulation framework** to evaluate downside scenarios beyond static spreadsheet models.

### Key Modelling Components

* **Monthly Cash Flow Modelling:** Integrated debt terms, interest rates, and vacancy periods.
* **Scenario-Based Stress Testing:** Evaluated DSCR sensitivity across a wide range of occupancy and interest rate assumptions.
* **Liquidity Runway Analysis:** Quantified the time threshold at which the project transitions from illiquid to insolvent.

$$DSCR = \frac{NOI}{\text{Debt Service (Interest + Principal)}}$$

---

## 4. Key Findings & Strategic Recommendations

* **Equity Role:** The current equity base functions primarily as an **interest carry buffer** rather than downside protection.
* **Probability of Insolvency:** Under base-case delays, the probability of **Equity Wipeout** exceeds 65% without intervention.
* **Strategic De-risking:** 1.  **Partial Pre-Sales:** Disposal of upper units to achieve debt paydown and reduce LTV to sub-80% levels.
    2.  **Liquidity Reserve:** Identification of specific cash reserve requirements to bridge the 14-month gap.

---

## 5. Project Organization (CCDS Structure)

This project follows the **Cookiecutter Data Science** standard for modularity and reproducibility.

```text
├── README.md          <- Project overview (this file)
├── data
│   ├── raw            <- Original data (Market deals, interest rate indices)
│   └── processed      <- Cleaned data for simulation input
├── notebooks          <- Jupyter notebooks for EDA and simulation runs
├── reports            <- Generated analysis and visual reports
│   └── figures        <- Visualisation outputs (Waterfall, Histograms)
├── requirements.txt   <- Python environment dependencies
└── pf_liquidity_risk  <- Source code for the analysis
    ├── config.py       <- Project constants (LTV limits, conversion rates)
    ├── dataset.py      <- Scripts to fetch and generate market data
    ├── modeling
    │   └── train.py    <- Monte Carlo simulation engine
    └── plots.py        <- Custom visualisation functions
```

## 6. Skills & Tools

* **Domain:** Real Estate Project Finance (PF), Risk Management, Capital Structure Optimization.
* **Technical:** Python (`Pandas`, `NumPy`, `Matplotlib`), Monte Carlo Simulation, Cash Flow Modelling.
* **Informatics:** Modular code design, data-driven decision support systems.

## 7. Key Takeaway

In highly leveraged development, **timing risk can be more destructive than market risk.** Proactive capital structure stress-testing enables earlier intervention and ensures downside protection before value impairment becomes irreversible.
