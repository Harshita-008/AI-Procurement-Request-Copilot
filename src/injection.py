"""Detect prompt-injection attempts inside business data (policy section 9)."""
from __future__ import annotations

import re

_PATTERNS = [
    r"ignore (all|any|the|previous|prior|above)\b[^.]*\b(rules?|instructions?|polic(y|ies)|controls?)",
    r"disregard\b[^.]*\b(rules?|instructions?|polic(y|ies))",
    r"bypass\b[^.]*\b(approval|review|control|polic)",
    r"treat (this|the) request as\b",
    r"\b(pre-?approved|already approved|cfo-approved|ceo-approved)\b",
    r"approve (it|this)( request)? (immediately|now|automatically)",
    r"\byou are now\b",
    r"\bsystem prompt\b",
    r"\bnew instructions?\b",
    r"\bact as (the|an?) (admin|approver|cfo|system)",
    r"\b(reveal|print|show|expose)\b[^.]*\b(secret|key|credential|prompt)",
]
_COMPILED = [re.compile(p, re.IGNORECASE) for p in _PATTERNS]

# Request fields and nested vendor notes that may carry free text.
TEXT_FIELDS = ("business_justification", "product_name", "vendor_name", "category", "data_access_level")


def scan_text(text: str | None, source: str) -> list[dict]:
    if not text:
        return []
    hits = []
    for pattern in _COMPILED:
        match = pattern.search(text)
        if match:
            hits.append({"source": source, "snippet": match.group(0)})
    return hits


def scan_request(request: dict, extra_texts: dict[str, str | None] | None = None) -> list[dict]:
    """Scan request text fields plus any extra untrusted strings (e.g. vendor notes)."""
    hits = []
    for field in TEXT_FIELDS:
        hits += scan_text(request.get(field), f"request.{field}")
    for item in request.get("requested_integrations") or []:
        hits += scan_text(str(item), "request.requested_integrations")
    for source, text in (extra_texts or {}).items():
        hits += scan_text(text, source)
    return hits
