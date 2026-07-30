"""
PF Configuration Data Model
Separated to avoid circular imports between engine.py and config files.
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

    # Monthly project-level overhead below property NOI (normalized units).
    # Kept as monthly_fixed_cost for backwards compatibility with local
    # configuration files; it is not a property operating expense.
    monthly_fixed_cost: float

    # Monthly property NOI distributions (Min, Mode, Max), after property
    # operating expenses but before project overhead and debt service.
    # The legacy field names are retained for backwards compatibility.
    stabilization_revenue_dist: Tuple[float, float, float]
    post_opening_revenue_dist: Tuple[float, float, float]

    # Capitalization rate for Income Approach valuation
    cap_rate: float = 0.055

    # Timeline (Months)
    completion_target_month: int = 16
    demand_driver_opening_month: int = 24
    exit_month: int = 36

    # Interest Rates (Min, Mode, Max) per Financing Stage
    pre_refi_rate: Tuple[float, float, float] = (0.10, 0.14, 0.18)  # Before refinancing
    post_refi_rate: Tuple[float, float, float] = (0.05, 0.07, 0.09)  # After refinancing

    # Refinancing & Exit Constraints
    target_refi_ltv_dist: Tuple[float, float, float] = (0.70, 0.80, 0.85)
    exit_cost_range: Tuple[float, float] = (0.01, 0.02)  # Transaction costs (1-2%)

    # One-time equity hit per delayed construction month, as a fraction of
    # monthly fixed cost (unrecoverable overhead: idle crew, extended G&A).
    delay_cost_factor: float = 0.6

    # Lease-up ramp after completion. The pre-signed anchor tenant provides an
    # NOI floor from day 1 (lease_up_initial_share of stabilized NOI);
    # the remaining floors ramp in linearly over stabilization_ramp_months
    # (fit-outs, rent-free periods). Default: 60% -> 80% -> 100%.
    stabilization_ramp_months: int = 3
    lease_up_initial_share: float = 0.6

    # Haircut applied to implied value in a forced sale after a failed
    # refinancing (distressed / time-constrained disposal).
    distress_sale_discount: float = 0.10

    # Metadata for display
    config_type: str = "unknown"
    display_currency: str = "Index"

    # Internal mapping for interest capitalization ratios
    # Defined in __post_init__ to avoid type check errors with default values.
    capitalized_ratio_map: Dict[str, float] = field(default_factory=dict, init=False)

    def __post_init__(self):
        if self.initial_equity <= 0:
            raise ValueError("initial_equity must be positive")
        if self.senior_loan < 0:
            raise ValueError("senior_loan cannot be negative")
        if self.monthly_fixed_cost < 0:
            raise ValueError("monthly_fixed_cost cannot be negative")
        if self.cap_rate <= 0:
            raise ValueError("cap_rate must be positive")

        self.capitalized_ratio_map = {
            "construction": 1.0,  # Full interest capitalization during building
            "stabilization": 0.4,  # Partial capitalization during ramp-up
            "exit": 0.0,  # No capitalization post-opening
        }

    @property
    def stabilization_noi_dist(self) -> Tuple[float, float, float]:
        """Domain-correct alias for the legacy stabilization field name."""
        return self.stabilization_revenue_dist

    @property
    def post_opening_noi_dist(self) -> Tuple[float, float, float]:
        """Domain-correct alias for the legacy post-opening field name."""
        return self.post_opening_revenue_dist
