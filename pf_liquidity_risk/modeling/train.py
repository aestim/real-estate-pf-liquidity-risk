import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from typing import Dict, List
from pathlib import Path

# Import config model (no circular dependency)
from pf_liquidity_risk.modeling.config_model import PFConfig
from pf_liquidity_risk.config import FIGURES_DIR

# Import public config by default - can be overridden for internal use
try:
    from pf_liquidity_risk.configs import private_config as config_module
    print("[CONFIG] Using private configuration (real data)")
except ImportError:
    from pf_liquidity_risk.configs import public_config as config_module
    print("[CONFIG] Using public configuration (normalized data)")


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

        principal_at_refi = 0.0
        refi_loan_amount = 0.0

        # Sample rates
        pre_refi_rate = np.random.triangular(*self.cfg.pre_refi_rate)
        post_refi_rate = np.random.triangular(*self.cfg.post_refi_rate)

        sampled_stab_rev = np.random.triangular(*self.cfg.stabilization_revenue_dist)
        sampled_post_rev = np.random.triangular(*self.cfg.post_court_revenue_dist)

        completion_month = self.cfg.completion_target_month + int(
            np.random.triangular(0, 2, 6)
        )
        delay = max(0, completion_month - self.cfg.completion_target_month)

        refi_month = completion_month + 3
        
        # Track refinancing status
        refinanced = False
        current_rate = pre_refi_rate

        for m in range(1, self.cfg.exit_month + 1):
            # Phase determination
            if m < completion_month:
                phase, revenue = "construction", 0
            elif m < self.cfg.court_opening_month:
                phase, revenue = "stabilization", sampled_stab_rev
            else:
                phase, revenue = "exit", sampled_post_rev

            revenue_history.append(revenue)

            # Interest rate logic
            monthly_rate = current_rate / 12
            interest = principal * monthly_rate
            cap_ratio = self.cfg.capitalized_ratio_map[phase]

            paid_interest = interest * (1 - cap_ratio)
            principal += (interest * cap_ratio)

            # Operating Cash Flow & Principal Sweep
            net_cash_flow = revenue - (self.cfg.monthly_fixed_cost + paid_interest)
            
            if net_cash_flow > 0:
                principal -= net_cash_flow
                if principal < 0:
                    equity += abs(principal)
                    principal = 0
            else:
                equity += net_cash_flow

            # Construction delay impact
            if m == completion_month and delay > 0:
                equity -= delay * self.cfg.monthly_fixed_cost * 0.6

            # Insolvency Check
            if equity <= 0:
                return {"status": "default", "month": m, "final_equity": 0, "irr": -1.0}

            # Refinancing Viability Check (Month (Completion + 3))
            if m == refi_month:
                ltv_limit = np.random.triangular(*self.cfg.target_refi_ltv_dist)
                operating_history = [rev for rev in revenue_history[-3:] if rev > 0]
                rolling_noi = np.mean(operating_history) if operating_history else revenue
                implied_val = (rolling_noi * 12) / self.cfg.cap_rate

                max_refi_loan = implied_val * ltv_limit
                principal_at_refi = principal
                refi_loan_amount = max_refi_loan
                
                if principal > (implied_val * ltv_limit):
                    # Refinancing failed
                    return {
                        "status": "refi_fail",
                        "month": m,
                        "final_equity": 0,
                        "irr": -1.0,
                        "principal_at_refi": principal_at_refi, "refi_loan_amount": refi_loan_amount
                        }
                else:
                    # Refinancing succeeded - switch to lower rate
                    refinanced = True
                    current_rate = post_refi_rate

            # Final Exit Transaction
            if m == self.cfg.exit_month:
                final_val = (revenue * 12) / self.cfg.cap_rate
                exit_cost = final_val * np.random.uniform(*self.cfg.exit_cost_range)
                exit_equity = final_val - principal - exit_cost

                if exit_equity > 0:
                    total_return = exit_equity / self.cfg.initial_equity
                    years = m / 12
                    irr = (total_return ** (1 / years)) - 1
                else:
                    irr = -1.0
                
                return {
                    "status": "exit", "month": m, "final_equity": max(0, exit_equity), "irr": irr,
                    "exit_multiple": exit_equity / self.cfg.initial_equity if exit_equity > 0 else 0,
                    "principal_at_refi": principal_at_refi, "refi_loan_amount": refi_loan_amount
                }

        return {
            "status": "survived_no_exit", "month": self.cfg.exit_month, "final_equity": equity, "irr": 0.0,
            "principal_at_refi": principal_at_refi, "refi_loan_amount": refi_loan_amount
            }


# ==========================================
# Execution & Visualization
# ==========================================

def run_simulation(iterations: int = 30000, seed: int = 42, config: PFConfig = None):
    """Executes the Monte Carlo simulation engine across specified iterations."""
    np.random.seed(seed)
    
    if config is None:
        config = config_module.get_config()
    
    model = PFInvestmentModel(config)
    results = [model.simulate_path() for _ in range(iterations)]
    return pd.DataFrame(results), config


def plot_enhanced_results(df: pd.DataFrame, iterations: int, config: PFConfig, filename: str):
    """
    Generates an analytical dashboard and saves it to the reports/figures directory.
    Uses semantic color mapping for project status.
    """
    plt.style.use("seaborn-v0_8-muted")
    fig, axes = plt.subplots(2, 2, figsize=(18, 12))
    axes = axes.flatten()

    # Semantic Color Map for professional risk reporting
    color_map = {
        "exit": "#2ECC71",           # Success - Green
        "default": "#E74C3C",        # Bankruptcy - Red
        "refi_fail": "#F1C40F",      # Liquidity Failure - Yellow/Orange
        "survived_no_exit": "#3498DB" # Partial - Blue
    }

    # 1. Outcome Distribution
    counts = df["status"].value_counts()
    colors = [color_map.get(s, "#BDC3C7") for s in counts.index]
    counts.plot(kind="bar", ax=axes[0], color=colors, edgecolor='black')
    axes[0].set_title("Project Outcome Distribution", fontweight='bold', fontsize=12)
    axes[0].set_ylabel("Frequency")
    axes[0].set_xlabel("")
    plt.setp(axes[0].get_xticklabels(), rotation=45, ha='right')
    
    # Add percentage labels
    for i, (idx, val) in enumerate(counts.items()):
        axes[0].text(i, val, f'{val/iterations*100:.1f}%', 
                    ha='center', va='bottom', fontweight='bold')

    # 2. Equity IRR Histogram
    exit_df = df[df["status"] == "exit"]
    if not exit_df.empty:
        exit_df["irr"].plot(kind="hist", bins=50, ax=axes[1], 
                           color='#3498DB', alpha=0.7, edgecolor='black')
        median_irr = exit_df["irr"].median()
        mean_irr = exit_df["irr"].mean()
        axes[1].axvline(median_irr, color='red', linestyle='--', 
                       linewidth=2, label=f'Median: {median_irr:.1%}')
        axes[1].axvline(mean_irr, color='green', linestyle='--', 
                       linewidth=2, label=f'Mean: {mean_irr:.1%}')
        axes[1].set_title("Equity IRR Distribution (Exit Cases)", fontweight='bold', fontsize=12)
        axes[1].set_xlabel("IRR")
        axes[1].set_ylabel("Frequency")
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)

    # 3. Survival Curve
    months = np.arange(1, 37)
    survival_rates = []
    for m in months:
        failed = df[df["status"].isin(["default", "refi_fail"]) & (df["month"] <= m)]
        survival_rates.append((iterations - len(failed)) / iterations)
    
    axes[2].plot(months, survival_rates, marker='o', markersize=4, 
                linewidth=2, color='#8E44AD')
    axes[2].fill_between(months, 0, survival_rates, alpha=0.3, color='#8E44AD')
    axes[2].set_ylim(0, 1.05)
    axes[2].set_title("Project Survival Rate Over Time", fontweight='bold', fontsize=12)
    axes[2].set_xlabel("Month")
    axes[2].set_ylabel("Survival Rate")
    axes[2].grid(True, alpha=0.3)
    axes[2].axhline(y=0.95, color='red', linestyle='--', alpha=0.5)
    axes[2].text(1, 0.96, '95% Threshold', fontsize=9)

    # 4. Exit Multiple Distribution
    if not exit_df.empty and "exit_multiple" in exit_df.columns:
        exit_df["exit_multiple"].plot(kind="hist", bins=40, ax=axes[3], 
                                      color='#27AE60', alpha=0.7, edgecolor='black')
        median_mult = exit_df["exit_multiple"].median()
        axes[3].axvline(median_mult, color='red', linestyle='--', 
                       linewidth=2, label=f'Median: {median_mult:.2f}x')
        axes[3].axvline(1.0, color='orange', linestyle=':', 
                       linewidth=2, label='Break-even (1.0x)')
        axes[3].set_title("Exit Multiple Distribution", fontweight='bold', fontsize=12)
        axes[3].set_xlabel("Multiple (Exit Equity / Initial Equity)")
        axes[3].set_ylabel("Frequency")
        axes[3].legend()
        axes[3].grid(True, alpha=0.3)

    plt.tight_layout()
    
    # Save the figure
    save_path = FIGURES_DIR / filename
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"\n[Visual] Visualization saved to: {save_path}")
    plt.close()


def print_summary_table(df: pd.DataFrame, config: PFConfig):
    """Print comprehensive risk analysis summary"""
    exit_df = df[df["status"] == "exit"]
    
    print("\n" + "="*70)
    print(f"    STOCHASTIC PF RISK ANALYSIS REPORT ({config.config_type})")
    print("="*70)
    
    print(f"\n[Configuration: {config.config_type}]")
    print("-" * 70)
    print(f"  Initial Equity       : {config.initial_equity:>12.2f} {config.display_currency}")
    print(f"  Senior Loan          : {config.senior_loan:>12.2f} {config.display_currency}")
    print(f"  Initial LTV          : {config.senior_loan/(config.senior_loan+config.initial_equity):>12.2%}")
    print(f"  Leverage Ratio       : {config.senior_loan/config.initial_equity:>12.2f}x")
    
    print("\n[Outcome Probabilities]")
    print("-" * 70)
    for status, count in df["status"].value_counts().items():
        prob = count / len(df) * 100
        print(f"  {status:20s}: {prob:>6.2f}% ({count:>6,} cases)")
    
    print("\n[Return Metrics - Exit Cases Only (n={:,})]".format(len(exit_df)))
    print("-" * 70)
    if not exit_df.empty:
        print(f"  Mean IRR             : {exit_df['irr'].mean():>8.2%}")
        print(f"  Median IRR           : {exit_df['irr'].median():>8.2%}")
        print(f"  Std Dev IRR          : {exit_df['irr'].std():>8.2%}")
        print(f"  25th Percentile      : {exit_df['irr'].quantile(0.25):>8.2%}")
        print(f"  75th Percentile      : {exit_df['irr'].quantile(0.75):>8.2%}")
        if "exit_multiple" in exit_df.columns:
            print(f"  Mean Exit Multiple   : {exit_df['exit_multiple'].mean():>8.2f}x")
            print(f"  Median Exit Multiple : {exit_df['exit_multiple'].median():>8.2f}x")
    
    print("\n[Risk Metrics]")
    print("-" * 70)
    loss = config.initial_equity - df["final_equity"]
    car_95 = np.percentile(loss, 95)
    car_99 = np.percentile(loss, 99)
    expected_loss = loss.mean()
    
    print(f"  Expected Loss        : {expected_loss/config.initial_equity:>8.2%} of equity")
    print(f"  95% VaR (CaR)        : {car_95/config.initial_equity:>8.2%} of equity")
    print(f"  99% VaR (CaR)        : {car_99/config.initial_equity:>8.2%} of equity")
    
    # Sharpe Ratio (for exit cases)
    if len(exit_df) > 0 and exit_df["irr"].std() > 0:
        sharpe = exit_df["irr"].mean() / exit_df["irr"].std()
        print(f"  Sharpe Ratio         : {sharpe:>8.2f}")
    
    print("\n" + "="*70)


def main():
    """
    Orchestration point: Define scenario parameters, run simulation, and trigger reporting.
    """
    iterations = 30000
    output_image = "pf_liquidity_analysis_v2.png"

    # Load configuration
    config = config_module.get_config()
    
    # Execution
    print(f"\n[START] Running {iterations:,} Monte Carlo iterations...")
    df, cfg = run_simulation(iterations, config=config)
    
    # Risk Reporting
    print_summary_table(df, cfg)
    
    # Generate Dashboard
    plot_enhanced_results(df, iterations, cfg, filename=output_image)
    
    print("\n[COMPLETE] Analysis finished!")


if __name__ == "__main__":
    main()