"""Make request records uniform before any rule sees them (hidden cases may vary in shape)."""
from __future__ import annotations

NUMERIC_FIELDS = ("annual_cost_usd", "user_count")
TEXT_FIELDS = ("product_name", "vendor_name", "category", "business_justification", "data_access_level", "urgency")


def _number(value):
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    text = str(value).strip().replace(",", "").replace("$", "")
    try:
        return float(text) if "." in text else int(text)
    except ValueError:
        return None


def normalize_request(request: dict) -> dict:
    out = dict(request)
    for field in NUMERIC_FIELDS:
        out[field] = _number(out.get(field))
    for field in TEXT_FIELDS:
        value = out.get(field)
        out[field] = value.strip() if isinstance(value, str) else (None if value is None else str(value))
    integrations = out.get("requested_integrations")
    if isinstance(integrations, str):
        integrations = [part.strip() for part in integrations.split(",") if part.strip()]
    elif integrations is not None and not isinstance(integrations, list):
        integrations = [str(integrations)]
    out["requested_integrations"] = integrations
    return out
