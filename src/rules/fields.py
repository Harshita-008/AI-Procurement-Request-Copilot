"""Policy section 1: required request information."""
from __future__ import annotations


def check_required_fields(request: dict, employee: dict | None, data_known: bool) -> list[str]:
    """Return human-readable descriptions of missing material information."""
    missing: list[str] = []
    if employee is None or not employee.get("department"):
        missing.append("requester or department could not be resolved")
    if not request.get("product_name") or not request.get("vendor_name"):
        missing.append("product or vendor name")
    if request.get("annual_cost_usd") is None:
        missing.append("annual cost (or a reasonable annual estimate)")
    if request.get("user_count") is None:
        missing.append("number of users/licenses")
    if not (request.get("business_justification") or "").strip():
        missing.append("business purpose")
    if not data_known:
        missing.append("intended data-access level")
    # An empty integrations list means "none needed"; only a missing field is a gap.
    if request.get("requested_integrations") is None:
        missing.append("required integrations")
    return missing
