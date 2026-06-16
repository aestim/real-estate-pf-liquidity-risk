"""
Public configuration with normalized/indexed values for portfolio demonstration.
All capital values are indexed to Initial Equity = 100.
"""

from pf_liquidity_risk.modeling.config_model import PFConfig


def get_config() -> PFConfig:
    """
    Returns normalized configuration for public portfolio use.
    """
    config = PFConfig(
        # Capital Structure (Indexed: Equity = 100)
        initial_equity=100.0,
        senior_loan=339.3,
        
        # Operating Costs (Indexed as % of equity)
        monthly_fixed_cost=1.79,
        
        # Monthly Revenue Distributions (Indexed)
        stabilization_revenue_dist=(0.89, 2.14, 2.68),
        post_court_revenue_dist=(2.14, 3.57, 4.46),
        
        config_type="PUBLIC (Normalized)",
        display_currency="Index"
    )
    
    return config