import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from dataclasses import dataclass, field
from typing import Dict, Tuple, List
from pf_liquidity_risk.config import FIGURES_DIR

# ==========================================
# PF Investment Model Configuration
# ==========================================

@dataclass
class PFConfig:
    """
    Configuration for Real Estate PF Investment Monte Carlo Simulation.
    Encapsulates all financial parameters and stochastic distributions.
    """

    # Capital Structure (KRW)
    initial_equity: float = 5_600_000_000
    senior_loan: float = 19_000_000_000

    # Operating Costs (KRW)
    monthly_fixed_cost: float = 100_000_000

    # Monthly Revenue Distributions (Min, Mode, Max)
    # Modeled as triangular distributions to reflect occupancy and market rent uncertainty.
    stabilization_revenue_dist: Tuple[float, float, float] = (50e6, 120e6, 150e6)
    post_court_revenue_dist: Tuple[float, float, float] = (120e6, 200e6, 250e6)
    
    # Capitalization rate for Income Approach valuation
    cap_rate: float = 0.055

    # Timeline (Months)
    completion_target_month: int = 16
    court_opening_month: int = 24
    exit_month: int = 36

    # Interest Rates (Min, Mode, Max) per Project Phase
    pre_completion_rate: Tuple[float, float, float] = (0.10, 0.14, 0.18)
    stabilization_rate: Tuple[float, float, float] = (0.08, 0.11, 0.14)
    post_court_rate: Tuple[float, float, float] = (0.05, 0.07, 0.09)

    # Internal mapping for interest capitalization ratios
    # Defined in __post_init__ to avoid type check errors with default values.
    capitalized_ratio_map: Dict[str, float] = field(init=False)

    def __post_init__(self):
        self.capitalized_ratio_map = {
            "construction": 1.0,   # Full interest capitalization during building
            "stabilization": 0.4,  # Partial capitalization during ramp-up
            "exit": 0.0            # No capitalization post-exit/court-opening
        }

    # Refinancing & Exit Constraints
    target_refi_ltv_dist: Tuple[float, float, float] = (0.70, 0.80, 0.85)
    exit_cost_range: Tuple[float, float] = (0.01, 0.02) # Transaction costs (1-2%)


# ==========================================
# Simulation Engine
# ==========================================

class PFInvestmentModel:
    """
    Handles the stochastic path generation for the project.
    Simulates monthly cash flows, debt accrual, and solvency checks.
    """
    def __init__(self, config: PFConfig):
        self.cfg = config

    def simulate_path(self) -> Dict:
        equity = self.cfg.initial_equity
        principal = self.cfg.senior_loan
        revenue_history: List[float] = []

        # Sampling interest rates for each phase at the start of the path
        rates = {
            "construction": np.random.triangular(*self.cfg.pre_completion_rate),
            "stabilization": np.random.triangular(*self.cfg.stabilization_rate),
            "exit": np.random.triangular(*self.cfg.post_court_rate)
        }

        # Sampling long-term performance targets
        sampled_stab_rev = np.random.triangular(*self.cfg.stabilization_revenue_dist)
        sampled_post_rev = np.random.triangular(*self.cfg.post_court_revenue_dist)

        # Construction delay logic (Triangular delay in months)
        completion_month = self.cfg.completion_target_month + int(
            np.random.triangular(0, 2, 6)
        )
        delay = max(0, completion_month - self.cfg.completion_target_month)

        for m in range(1, self.cfg.exit_month + 1):
            # Phase determination
            if m < completion_month:
                phase, revenue = "construction", 0
            elif m < self.cfg.court_opening_month:
                phase, revenue = "stabilization", sampled_stab_rev
            else:
                phase, revenue = "exit", sampled_post_rev

            revenue_history.append(revenue)

            # Monthly interest calculation
            monthly_rate = rates[phase] / 12
            interest = principal * monthly_rate
            cap_ratio = self.cfg.capitalized_ratio_map[phase]

            paid_interest = interest * (1 - cap_ratio)
            principal += (interest * cap_ratio) # Debt inflation via capitalization

            # Operating Cash Flow & Principal Sweep
            net_cash_flow = revenue - (self.cfg.monthly_fixed_cost + paid_interest)
            
            if net_cash_flow > 0:
                # Use surplus to pay down debt (Cash Sweep)
                principal -= net_cash_flow
                if principal < 0:
                    equity += abs(principal)
                    principal = 0
            else:
                # Deficit reduces equity buffer
                equity += net_cash_flow

            # Impact of construction delays on equity
            if m == completion_month and delay > 0:
                equity -= delay * self.cfg.monthly_fixed_cost * 0.6

            # Insolvency Check: Immediate default if equity wiped out
            if equity <= 0:
                return {"status": "default", "month": m, "final_equity": 0}

            # Refinancing Viability Check (Month 24)
            if m == self.cfg.court_opening_month:
                ltv_limit = np.random.triangular(*self.cfg.target_refi_ltv_dist)
                # Income Approach: Using 6-month rolling NOI for market valuation
                rolling_noi = np.mean(revenue_history[-6:])
                implied_val = (rolling_noi * 12) / self.cfg.cap_rate
                
                # Failure if current debt exceeds bank's LTV limit
                if principal > (implied_val * ltv_limit):
                    return {"status": "refi_fail", "month": m, "final_equity": 0}

            # Final Exit Transaction (Month 36)
            if m == self.cfg.exit_month:
                final_val = (revenue * 12) / self.cfg.cap_rate
                exit_cost = final_val * np.random.uniform(*self.cfg.exit_cost_range)
                exit_equity = final_val - principal - exit_cost

                # Calculate Equity IRR
                irr = (exit_equity / self.cfg.initial_equity) ** (12 / m) - 1 if exit_equity > 0 else -1.0
                return {
                    "status": "exit",
                    "month": m,
                    "final_equity": max(0, exit_equity),
                    "irr": irr
                }

        return {"status": "survived_no_exit", "month": self.cfg.exit_month, "final_equity": equity}


# ==========================================
# Execution & Visualization
# ==========================================

def run_simulation(iterations: int = 30000, seed: int = 42):
    """Executes the Monte Carlo simulation engine across specified iterations."""
    np.random.seed(seed)
    cfg = PFConfig()
    model = PFInvestmentModel(cfg)
    results = [model.simulate_path() for _ in range(iterations)]
    return pd.DataFrame(results), cfg

def plot_enhanced_results(df: pd.DataFrame, iterations: int, filename: str):
    """
    Generates an analytical dashboard and saves it to the reports/figures directory.
    Uses semantic color mapping for project status.
    """
    plt.style.use("seaborn-v0_8-muted")
    fig, axes = plt.subplots(1, 3, figsize=(20, 6))

    # Semantic Color Map for professional risk reporting
    color_map = {
        "exit": "#2ECC71",           # Success - Green
        "default": "#E74C3C",        # Bankruptcy - Red
        "refi_fail": "#F1C40F",       # Liquidity Failure - Yellow/Orange
        "survived_no_exit": "#3498DB" # Partial - Blue
    }

    # 1. Outcome Distribution
    counts = df["status"].value_counts()
    colors = [color_map.get(s, "#BDC3C7") for s in counts.index]
    counts.plot(kind="bar", ax=axes[0], color=colors)
    axes[0].set_title("Project Outcome Distribution", fontweight='bold')
    axes[0].set_ylabel("Frequency")
    plt.setp(axes[0].get_xticklabels(), rotation=0)

    # 2. Equity IRR Histogram
    if "irr" in df.columns:
        exit_df = df[df["status"] == "exit"]
        if not exit_df.empty:
            exit_df["irr"].plot(kind="hist", bins=50, ax=axes[1], color='#3498DB', alpha=0.7)
            median_irr = exit_df["irr"].median()
            axes[1].axvline(median_irr, color='red', linestyle='--', label=f'Median: {median_irr:.1%}')
            axes[1].set_title("Equity IRR Distribution (Exits Only)", fontweight='bold')
            axes[1].legend()

    # 3. Dynamic Survival Curve
    months = np.arange(1, 37)
    survival_rates = []
    for m in months:
        # Paths that have NOT failed (default or refi_fail) by month m
        failed_so_far = df[df["status"].isin(["default", "refi_fail"]) & (df["month"] <= m)]
        survival_rates.append((iterations - len(failed_so_far)) / iterations)
    
    axes[2].plot(months, survival_rates, marker='o', markersize=3, color='#8E44AD')
    axes[2].set_ylim(0, 1.05)
    axes[2].set_title("Project Survival Rate Over Time", fontweight='bold')
    axes[2].set_xlabel("Month")
    axes[2].grid(True, alpha=0.3)

    plt.tight_layout()
    
    # Save the figure to the specified path
    save_path = FIGURES_DIR / filename
    plt.savefig(save_path, dpi=300)
    print(f"\n[Visual] Visualization saved to: {save_path}")
    plt.show()


def main():
    """
    Orchestration point: Define scenario parameters, run simulation, and trigger reporting.
    """
    iterations = 30000
    output_image = "pf_liquidity_analysis_v1.png"

    # Execution
    df, cfg = run_simulation(iterations)
    
    # Risk Reporting (CLI Output)
    print("\n" + "="*45)
    print("    STOCHASTIC PF RISK ANALYSIS REPORT")
    print("="*45)
    print("\n[Outcome Probabilities]")
    print(df["status"].value_counts(normalize=True))
    
    # Quantifying Capital at Risk (CaR)
    loss = cfg.initial_equity - df["final_equity"]
    car_95 = np.percentile(loss, 95)
    print(f"\n[Value at Risk] 95% Capital at Risk: {car_95/1e9:.2f} B KRW")
    
    # Generate Dashboard
    plot_enhanced_results(df, iterations, filename=output_image)

if __name__ == "__main__":
    main()