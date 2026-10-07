"""Value-level grounding: numbers and dates quoted in model findings must exist in data the model saw."""
from __future__ import annotations

import json
import re

from src.data_access import load_policy_text

# A number, optionally followed by a k/M shorthand suffix ("$25k", "1.5M").
_NUMBER = re.compile(r"(\d[\d,]*\.?\d*)\s*([kKmM]\b)?")
_SUFFIX = {"k": 1_000, "m": 1_000_000}


def numbers_in(text: str) -> set[str]:
    """Numbers in a text, normalised so '29,000', '29000', '29000.0' and '29k' compare equal."""
    found = set()
    for raw, suffix in _NUMBER.findall(text or ""):
        cleaned = raw.replace(",", "").rstrip(".")
        try:
            found.add(format(float(cleaned) * _SUFFIX.get(suffix.lower(), 1), "g"))
        except ValueError:
            continue
    return found


def known_values(tool_outputs: list, request: dict) -> set[str]:
    """Every number the model could legitimately quote: tool results, the request, the policy text."""
    text = json.dumps(tool_outputs, default=str) + json.dumps(request, default=str) + load_policy_text()
    return numbers_in(text)


def unverified_values(finding: str, known: set[str]) -> list[str]:
    return sorted(numbers_in(finding) - known)
