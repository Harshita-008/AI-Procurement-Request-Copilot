"""Policy section 3: existing software overlap."""
from __future__ import annotations


def _norm(value) -> str:
    return str(value or "").strip().lower()


def find_overlap(product_name: str, vendor_name: str, category: str, catalog: list[dict]) -> list[dict]:
    """Return catalog rows that overlap, each tagged with the strongest match kind."""
    product, vendor, cat = _norm(product_name), _norm(vendor_name), _norm(category)
    matches = []
    for row in catalog:
        row_product, row_vendor, row_cat = _norm(row["product_name"]), _norm(row["vendor_name"]), _norm(row["category"])
        if row_product and (row_product in product or product in row_product):
            kind = "same_product"
        elif row_vendor and row_vendor == vendor:
            kind = "same_vendor"
        elif row_cat and row_cat == cat:
            kind = "same_category"
        else:
            continue
        matches.append({"match_kind": kind, **row})
    order = {"same_product": 0, "same_vendor": 1, "same_category": 2}
    return sorted(matches, key=lambda m: order[m["match_kind"]])
