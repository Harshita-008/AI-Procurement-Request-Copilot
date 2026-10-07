"""Tool 2: existing software catalog overlap and purchase history."""
from __future__ import annotations

from src.data_access import load_purchase_history, load_software_catalog
from src.rules.overlap import find_overlap


def search_software_catalog(ctx, product_name: str, vendor_name: str, category: str = "") -> dict:
    matches = find_overlap(product_name, vendor_name, category, load_software_catalog())
    vendor = (vendor_name or "").strip().lower()
    history = [p for p in load_purchase_history() if str(p["vendor_name"]).strip().lower() == vendor]
    return {
        "matches": matches,
        "match_kinds": sorted({m["match_kind"] for m in matches}),
        "purchase_history": history,
    }
