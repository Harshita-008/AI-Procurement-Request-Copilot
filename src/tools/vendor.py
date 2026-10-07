"""Tool 3: internal vendor registry + external vendor-risk API, with conflict detection."""
from __future__ import annotations

from src.data_access import load_vendors
from src.injection import scan_text
from src.rules.vendor import assess_vendor
from src.vendor_client import fetch_vendor_risk


def get_vendor_status(ctx, vendor_name: str) -> dict:
    name = (vendor_name or "").strip().lower()
    registry = next((v for v in load_vendors() if str(v["vendor_name"]).strip().lower() == name), None)
    record, availability, error = fetch_vendor_risk(vendor_name)

    # Vendor notes are untrusted business data; scan them like request text.
    flags = scan_text(registry.get("notes") if registry else None, "vendor_registry.notes")
    flags += scan_text(record.get("notes") if record else None, "vendor_risk_api.notes")

    return {
        "vendor_name": vendor_name,
        "registry": registry,
        "risk_service": {"availability": availability, "record": record, "error": error},
        "assessment": assess_vendor(registry, record, availability),
        "untrusted_text_flags": flags,
    }
