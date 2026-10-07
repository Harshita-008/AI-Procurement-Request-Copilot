"""Tools 4 and 5: deterministic policy checks and policy text lookup."""
from __future__ import annotations

import re

from src.data_access import load_policy_text
from src.rules.engine import evaluate_policy


def run_policy_checks(ctx) -> dict:
    """Gathers evidence via the other tools (cached) and applies every deterministic rule."""
    req = ctx.request
    requester = ctx.call("get_requester_and_budget", {"requester_id": req.get("requester_id")}, internal=True)
    catalog = ctx.call("search_software_catalog", {
        "product_name": req.get("product_name") or "",
        "vendor_name": req.get("vendor_name") or "",
        "category": req.get("category") or "",
    }, internal=True)
    vendor = ctx.call("get_vendor_status", {"vendor_name": req.get("vendor_name") or ""}, internal=True)
    return evaluate_policy(req, requester, catalog, vendor).model_dump()


def _sections() -> list[dict]:
    text = load_policy_text()
    parts = re.split(r"^## ", text, flags=re.MULTILINE)[1:]
    out = []
    for part in parts:
        title, _, body = part.partition("\n")
        number = title.split(".")[0].strip()
        out.append({"section": number, "title": title.strip(), "text": body.strip()})
    return out


def lookup_policy(ctx, topics: list[str] | None = None) -> dict:
    """Return policy sections matching section numbers or keywords; all titles if none match."""
    sections = _sections()
    wanted = [str(t).strip().lower() for t in (topics or [])]
    if not wanted:
        return {"sections": [{"section": s["section"], "title": s["title"]} for s in sections]}
    hits = [s for s in sections if any(w == s["section"] or w in s["title"].lower() or w in s["text"].lower() for w in wanted)]
    return {"sections": hits or [{"section": s["section"], "title": s["title"]} for s in sections]}
