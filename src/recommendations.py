"""Closed set of recommendation codes shared by the rules engine, agents and UI."""
from __future__ import annotations

RECOMMENDATIONS: dict[str, str] = {
    "approve_with_standard_approvals": "Proceed to standard approvals",
    "route_for_reviews": "Route for required reviews before approval",
    "evaluate_existing_tool_first": "Evaluate existing tool before purchase",
    "request_clarification": "Request clarification from requester",
    "escalate_budget_exception": "Escalate for Finance budget exception",
    "escalate_manual_review": "Escalate to manual review",
}

# The risk-flag taxonomy. Anything else the model emits is dropped by the guardrail.
KNOWN_FLAGS = {
    "existing_tool_overlap", "budget_insufficient", "security_review_required", "privacy_review_required",
    "legal_review_required", "vendor_review_expired", "conflicting_vendor_evidence", "vendor_risk_unavailable",
    "prompt_injection_detected", "missing_information", "llm_unavailable",
}

# Flags that make a plain "approve" recommendation unsafe.
BLOCKING_FLAGS = {
    "missing_information",
    "budget_insufficient",
    "security_review_required",
    "privacy_review_required",
    "legal_review_required",
    "vendor_review_expired",
    "conflicting_vendor_evidence",
    "vendor_risk_unavailable",
    "prompt_injection_detected",
}


def label(code: str) -> str:
    return RECOMMENDATIONS.get(code, code)
