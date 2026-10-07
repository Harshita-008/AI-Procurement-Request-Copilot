"""Policy sections 2 and 4: budget check and financial approval thresholds."""
from __future__ import annotations

APPROVAL_TIERS = [
    (1_000, ["Manager"]),
    (10_000, ["Department Head", "Procurement"]),
    (25_000, ["Department Head", "Finance", "Procurement"]),
    (float("inf"), ["Department Head", "Finance", "CFO", "Procurement"]),
]


def check_budget(cost: float | None, available: float | None) -> dict:
    if cost is None or available is None:
        return {"status": "unknown", "cost_usd": cost, "available_usd": available, "shortfall_usd": None}
    shortfall = max(0.0, float(cost) - float(available))
    return {
        "status": "exceeds" if shortfall > 0 else "within",
        "cost_usd": cost,
        "available_usd": available,
        "shortfall_usd": shortfall or None,
    }


def approval_tier(cost: float | None) -> dict:
    """Minimum business approvals for the annualised amount. Manager floor if cost unknown."""
    if cost is None:
        return {"tier": "undetermined", "approvals": ["Manager"]}
    for limit, approvals in APPROVAL_TIERS:
        if cost <= limit:
            label = f"up to ${limit:,.0f}" if limit != float("inf") else "above $25,000"
            return {"tier": label, "approvals": list(approvals)}
    raise AssertionError("unreachable")
