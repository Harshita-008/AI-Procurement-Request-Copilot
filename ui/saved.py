"""Load decisions saved by evals/run_comparison.py so the UI works without a model key."""
from __future__ import annotations

import json

from src.config import ROOT

DECISIONS_DIR = ROOT / "evals" / "results" / "decisions"


def find_saved(request_id: str, architecture: str) -> dict | None:
    folder = DECISIONS_DIR / architecture
    if not folder.exists():
        return None
    for path in sorted(folder.glob("*.json"), reverse=True):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("request_id") == request_id:
            return data
    return None
