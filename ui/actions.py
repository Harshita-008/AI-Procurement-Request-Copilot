"""Human review actions: the copilot recommends, people decide. Decisions are logged, never executed."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from src.config import ROOT
from src.recommendations import label

LOG_PATH = ROOT / "outputs" / "review_log.jsonl"

# Buttons shown to the reviewer.
ACTIONS = {
    "send_for_review": "Send to approvers / reviewers",
    "request_clarification": "Request clarification from requester",
    "return_to_requester": "Return (existing tool / not approved)",
}
# The reviewer disagrees and records their own recommendation with a reason.
OVERRIDE_ACTION = "override"
ACTION_LABELS = {**ACTIONS, OVERRIDE_ACTION: "Override recommendation"}


def log_action(request_id: str, architecture: str, action: str, reviewer: str, note: str, decision: dict,
               override_code: str | None = None) -> dict:
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
    if override_code:
        entry["override_code"] = override_code
    LOG_PATH.parent.mkdir(exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def load_actions(request_id: str) -> list[dict]:
    if not LOG_PATH.exists():
        return []
    entries = [json.loads(line) for line in LOG_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [e for e in entries if e["request_id"] == request_id]


def describe(entry: dict) -> str:
    """One-line history text; overrides show the reviewer's recommendation."""
    text = ACTION_LABELS.get(entry["action"], entry["action"])
    if entry.get("override_code"):
        text += f" → {label(entry['override_code'])}"
    return text
