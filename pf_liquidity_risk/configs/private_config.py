"""
PRIVATE CONFIGURATION - INTERNAL USE ONLY
"""

from pf_liquidity_risk.modeling.config_model import PFConfig


def get_config() -> PFConfig:
    """
    Returns actual project configuration with real financial data.
    
    *** CONFIDENTIAL - INTERNAL USE ONLY ***
    """
    config = PFConfig(
        initial_equity=5_600_000_000,
        senior_loan=19_000_000_000,
        monthly_fixed_cost=100_000_000,
        stabilization_revenue_dist=(50e6, 120e6, 150e6),
        post_court_revenue_dist=(120e6, 200e6, 250e6),
        config_type="PRIVATE (Real Data)",
        display_currency="KRW"
    )
    
    return config