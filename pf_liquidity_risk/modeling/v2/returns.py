"""Equity return helpers with explicit monthly cash-flow timing."""

import math
from typing import Sequence


def periodic_irr(
    cash_flows: Sequence[float],
    *,
    periods_per_year: int = 12,
    tolerance: float = 1e-10,
    max_iterations: int = 300,
) -> float | None:
    """Return annualized IRR for equally spaced cash flows.

    The implementation uses a bounded bisection search and returns ``None``
    when the cash-flow series has no conventional sign change or no bracketed
    root. It does not claim to resolve multiple-IRR cash-flow profiles.
    """

    values = [float(value) for value in cash_flows]
    if (
        not values
        or not any(value < 0 for value in values)
        or not any(value > 0 for value in values)
    ):
        return None
    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be positive")
    if tolerance <= 0:
        raise ValueError("tolerance must be positive")

    def npv(rate: float) -> float:
        return sum(value / (1 + rate) ** period for period, value in enumerate(values))

    low = -0.9999
    high = 1.0
    low_value = npv(low)
    high_value = npv(high)
    while low_value * high_value > 0 and high < 1_000:
        high *= 2
        high_value = npv(high)
    if low_value * high_value > 0:
        return None

    monthly_rate = 0.0
    for _ in range(max_iterations):
        monthly_rate = (low + high) / 2
        value = npv(monthly_rate)
        if abs(value) <= tolerance:
            break
        if low_value * value <= 0:
            high = monthly_rate
            high_value = value
        else:
            low = monthly_rate
            low_value = value

    annualized = (1 + monthly_rate) ** periods_per_year - 1
    return annualized if math.isfinite(annualized) else None


def realized_equity_multiple(cash_flows: Sequence[float]) -> float:
    """Return positive distributions divided by absolute contributions."""

    contributions = -sum(min(float(value), 0.0) for value in cash_flows)
    distributions = sum(max(float(value), 0.0) for value in cash_flows)
    if contributions <= 0:
        return 0.0
    return distributions / contributions
