"""Contract-driven V2 development, operating, refinancing, and stress model.

V2 is built beside the legacy engine. It provides reconciled monthly ledgers,
bottom-up NOI, take-out and sale waterfalls, monthly equity returns, and a
regime-correlated Monte Carlo wrapper.
"""

from pf_liquidity_risk.modeling.v2.config import (
    DevelopmentLedgerConfig,
    DevelopmentSources,
    DevelopmentTimeline,
    DevelopmentUses,
    FinancingTerms,
    build_base_case_config,
)
from pf_liquidity_risk.modeling.v2.leasing import (
    LeaseSegment,
    OperatingLedgerConfig,
    OperatingLedgerInvariantError,
    OperatingLedgerResult,
    build_base_operating_config,
    build_operating_ledger,
    validate_operating_ledger,
)
from pf_liquidity_risk.modeling.v2.ledger import (
    DevelopmentLedgerResult,
    LedgerInvariantError,
    build_development_ledger,
    validate_ledger,
)
from pf_liquidity_risk.modeling.v2.monte_carlo import (
    REGIMES,
    MacroRegime,
    ScenarioDraw,
    build_scenario_config,
    run_v2_monte_carlo,
    sample_scenario,
    smooth_cost_weights,
    summarize_v2_results,
)
from pf_liquidity_risk.modeling.v2.project import (
    ProjectLedgerInvariantError,
    ProjectV2Config,
    ProjectV2Result,
    ResolutionTerms,
    build_base_project_config,
    run_project,
    validate_project_ledger,
)
from pf_liquidity_risk.modeling.v2.refinance import (
    RefinanceDecision,
    TakeoutCapacity,
    TakeoutTerms,
    fund_refinance,
    size_takeout,
)
from pf_liquidity_risk.modeling.v2.returns import (
    periodic_irr,
    realized_equity_multiple,
)
from pf_liquidity_risk.modeling.v2.waterfall import (
    SaleTerms,
    SaleWaterfallResult,
    run_sale_waterfall,
)

__all__ = [
    "DevelopmentLedgerConfig",
    "DevelopmentLedgerResult",
    "DevelopmentSources",
    "DevelopmentTimeline",
    "DevelopmentUses",
    "FinancingTerms",
    "LeaseSegment",
    "LedgerInvariantError",
    "MacroRegime",
    "OperatingLedgerConfig",
    "OperatingLedgerInvariantError",
    "OperatingLedgerResult",
    "ProjectLedgerInvariantError",
    "ProjectV2Config",
    "ProjectV2Result",
    "RefinanceDecision",
    "ResolutionTerms",
    "REGIMES",
    "SaleTerms",
    "SaleWaterfallResult",
    "ScenarioDraw",
    "TakeoutCapacity",
    "TakeoutTerms",
    "build_base_case_config",
    "build_base_operating_config",
    "build_base_project_config",
    "build_scenario_config",
    "build_development_ledger",
    "build_operating_ledger",
    "fund_refinance",
    "periodic_irr",
    "realized_equity_multiple",
    "run_project",
    "run_sale_waterfall",
    "run_v2_monte_carlo",
    "sample_scenario",
    "size_takeout",
    "smooth_cost_weights",
    "summarize_v2_results",
    "validate_ledger",
    "validate_operating_ledger",
    "validate_project_ledger",
]
