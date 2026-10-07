"""Policy section 3: existing software overlap."""
from __future__ import annotations

# Strongest first. Only same_product can be a duplicate; the rest are informational.
MATCH_ORDER = ("same_product", "related_product", "same_vendor", "same_category")


def _norm(value) -> str:
    return str(value or "").strip().lower()


def _match_kind(product: str, vendor: str, category: str, row: dict) -> str | None:
    row_product, row_vendor, row_cat = _norm(row["product_name"]), _norm(row["vendor_name"]), _norm(row["category"])
    name_overlaps = bool(row_product) and (row_product in product or product in row_product)
    if name_overlaps:
        # Same category = possible duplicate; different category = add-on, service or training for the tool.
        return "same_product" if (not category or row_cat == category) else "related_product"
    if row_vendor and row_vendor == vendor:
        return "same_vendor"
    if row_cat and row_cat == category:
        return "same_category"
    return None


def find_overlap(product_name: str, vendor_name: str, category: str, catalog: list[dict]) -> list[dict]:
    """Return catalog rows that overlap, each tagged with the strongest match kind."""
    product, vendor, cat = _norm(product_name), _norm(vendor_name), _norm(category)
    matches = []
    for row in catalog:
        kind = _match_kind(product, vendor, cat, row)
        if kind:
            matches.append({"match_kind": kind, **row})
    return sorted(matches, key=lambda m: MATCH_ORDER.index(m["match_kind"]))
