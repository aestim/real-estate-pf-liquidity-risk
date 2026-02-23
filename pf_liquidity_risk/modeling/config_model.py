"""
PF Configuration Data Model
Separated to avoid circular imports between train.py and config files.
"""

from dataclasses import dataclass, field
from typing import Dict, Tuple


@dataclass
class PFConfig:
    """
    Configuration for Real Estate PF Investment Monte Carlo Simulation.
    Encapsulates all financial parameters and stochastic distributions.
    """

    # Capital Structure (normalized units)
    initial_equity: float
    senior_loan: float

    # Operating Costs (normalized units)
    monthly_fixed_cost: float

    # Monthly Revenue Distributions (Min, Mode, Max)
    # Modeled as triangular distributions to reflect occupancy and market rent uncertainty.
    stabilization_revenue_dist: Tuple[float, float, float]
    post_court_revenue_dist: Tuple[float, float, float]
    
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

    # Refinancing & Exit Constraints
    target_refi_ltv_dist: Tuple[float, float, float] = (0.70, 0.80, 0.85)
    exit_cost_range: Tuple[float, float] = (0.01, 0.02)  # Transaction costs (1-2%)
    
    # Metadata for display
    config_type: str = "unknown"
    display_currency: str = "Index"
    
    # Internal mapping for interest capitalization ratios
    # Defined in __post_init__ to avoid type check errors with default values.
    capitalized_ratio_map: Dict[str, float] = field(default_factory=dict, init=False)

    def __post_init__(self):
        self.capitalized_ratio_map = {
            "construction": 1.0,   # Full interest capitalization during building
            "stabilization": 0.4,  # Partial capitalization during ramp-up
            "exit": 0.0            # No capitalization post-exit/court-opening
        }