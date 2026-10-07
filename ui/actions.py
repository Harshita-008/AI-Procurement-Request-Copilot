"""Human review actions: the copilot recommends, people decide. Decisions are logged, never executed."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from src.config import ROOT

LOG_PATH = ROOT / "outputs" / "review_log.jsonl"

ACTIONS = {
    "send_for_review": "Send to approvers / reviewers",
    "request_clarification": "Request clarification from requester",
    "return_to_requester": "Return (existing tool / not approved)",
}


def log_action(request_id: str, architecture: str, action: str, reviewer: str, note: str, decision: dict) -> dict:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "request_id": request_id,
        "architecture": architecture,
        "action": action,
        "reviewer": reviewer or "anonymous",
        "note": note,
        "recommendation_code": decision.get("recommendation_code"),
        "required_approvals": decision.get("required_approvals"),
    }
    LOG_PATH.parent.mkdir(exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def load_actions(request_id: str) -> list[dict]:
    if not LOG_PATH.exists():
        return []
    entries = [json.loads(line) for line in LOG_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [e for e in entries if e["request_id"] == request_id]
