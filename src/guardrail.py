"""Code guardrail: the model's draft can never be weaker than deterministic policy."""
from __future__ import annotations

from src.agents.schemas import ModelDecision
from src.grounding import unverified_values
from src.recommendations import BLOCKING_FLAGS, KNOWN_FLAGS, label
from src.rules.engine import APPROVAL_ORDER, PolicyResult

APPROVAL_ALIASES = {
    "manager": "Manager", "line manager": "Manager", "department head": "Department Head",
    "dept head": "Department Head", "head of department": "Department Head", "procurement": "Procurement",
    "finance": "Finance", "cfo": "CFO", "security": "Security", "it security": "Security",
    "infosec": "Security", "privacy": "Privacy", "dpo": "Privacy", "legal": "Legal",
}
# Deterministic evidence each tool already covers, so gaps are filled without duplicates.
EVIDENCE_COVERAGE = {
    "get_requester_and_budget": {"budget_check"},
    "search_software_catalog": {"catalog_overlap"},
    "get_vendor_status": {"vendor_status"},
    "run_policy_checks": {"approval_thresholds", "data_classification", "required_fields", "injection_scan"},
}

# Flags where code is the source of truth in both directions.
CODE_OWNED_FLAGS = {"budget_insufficient", "vendor_risk_unavailable", "vendor_review_expired",
                    "conflicting_vendor_evidence", "missing_information"}


def normalize_approval(name: str) -> str:
    key = name.strip().lower().replace("_", " ")
    for alias, canonical in APPROVAL_ALIASES.items():
        if alias in key:
            return canonical
    return name.strip()


def same_topic(a: str, b: str) -> bool:
    """True when two free-text items share a word stem (e.g. 'user_count' vs 'number of users/licenses')."""
    def stems(text: str) -> set[str]:
        words = text.lower().replace("_", " ").replace("/", " ").replace("-", " ").split()
        return {w[:4] for w in words if len(w) >= 4}
    return bool(stems(a) & stems(b))


def normalize_flag(flag: str) -> str:
    return flag.strip().lower().replace(" ", "_").replace("-", "_")


def apply_guardrail(draft: ModelDecision, policy: PolicyResult, tools_used: set[str],
                    known: set[str] | None = None) -> tuple[dict, list[str]]:
    """Return (decision fields, corrections). `known` = numbers the model saw; None skips value checks."""
    corrections: list[str] = []

    approvals = {normalize_approval(a) for a in draft.required_approvals}
    for needed in policy.required_approvals:
        if needed not in approvals:
            approvals.add(needed)
            corrections.append(f"added approval: {needed}")
    ordered = [a for a in APPROVAL_ORDER if a in approvals] + sorted(a for a in approvals if a not in APPROVAL_ORDER)

    flags = {normalize_flag(f) for f in draft.risk_flags}
    for flag in sorted(flags - KNOWN_FLAGS):
        corrections.append(f"dropped non-taxonomy risk flag: {flag}")
    flags &= KNOWN_FLAGS
    policy_flags = set(policy.risk_flags)
    for flag in policy_flags - flags:
        corrections.append(f"added risk flag: {flag}")
    for flag in (flags & CODE_OWNED_FLAGS) - policy_flags:
        corrections.append(f"removed unsupported risk flag: {flag}")
    flags = (flags - (CODE_OWNED_FLAGS - policy_flags)) | policy_flags

    missing = list(policy.missing_information)
    for item in policy.missing_information:
        if not any(same_topic(item, m) for m in draft.missing_information):
            corrections.append(f"added missing information: {item}")
    for item in draft.missing_information:
        if not any(same_topic(item, known) for known in missing):
            corrections.append(f"dropped model-added missing information (policy §1 lists none): {item}")

    allowed_sources = tools_used | {e["source"] for e in policy.evidence}
    evidence = []
    for item in draft.evidence:
        if item.source not in allowed_sources:
            corrections.append(f"dropped ungrounded evidence from '{item.source}'")
            continue
        bad_values = unverified_values(item.finding, known) if known is not None else []
        if bad_values:
            corrections.append(f"dropped evidence from '{item.source}' quoting values not in any tool result: {bad_values}")
            continue
        evidence.append({"source": item.source, "finding": item.finding, "reference": item.reference or None})
    covered = set().union(*(EVIDENCE_COVERAGE.get(e["source"], set()) for e in evidence)) if evidence else set()
    for item in policy.evidence:
        if item["source"] not in covered:
            evidence.append(dict(item))
            corrections.append(f"added deterministic evidence: {item['source']}")

    code = draft.recommendation_code
    if code == "approve_with_standard_approvals" and flags & BLOCKING_FLAGS:
        code = policy.suggested_recommendation_code
        corrections.append(f"recommendation downgraded from approve to {code}")
    elif policy.suggested_recommendation_code == "request_clarification" and code != "request_clarification":
        code = "request_clarification"
        corrections.append("recommendation set to request_clarification (material information missing)")
    elif "budget_insufficient" in flags and code not in {"escalate_budget_exception", "escalate_manual_review"}:
        code = "escalate_budget_exception"
        corrections.append("recommendation set to escalate_budget_exception (policy §2: cost exceeds available budget)")

    return {
        "recommendation": label(code),
        "recommendation_code": code,
        "summary": draft.summary,
        "evidence": evidence,
        "required_approvals": ordered,
        "missing_information": missing,
        "risk_flags": sorted(flags),
        "next_step": draft.next_step or default_next_step(code, ordered),
        "human_review_required": True,
    }, corrections


def default_next_step(code: str, approvals: list[str]) -> str:
    who = ", ".join(approvals) or "Procurement"
    steps = {
        "approve_with_standard_approvals": f"Send to {who} for approval.",
        "route_for_reviews": f"Send the evidence package to {who} for review before any approval.",
        "evaluate_existing_tool_first": "Procurement to confirm with the requester whether the existing catalog tool meets the need before purchasing.",
        "request_clarification": "Procurement to ask the requester for the missing information before review continues.",
        "escalate_budget_exception": "Finance to decide on a budget exception; other reviews proceed in parallel.",
        "escalate_manual_review": "Procurement and Security to manually verify vendor status before any approval.",
    }
    return steps.get(code, f"Route to {who} for human review.")


def rules_only_decision(policy: PolicyResult) -> dict:
    """Decision built purely from deterministic rules (fallback and comparison baseline)."""
    code = policy.suggested_recommendation_code
    return {
        "recommendation": label(code),
        "recommendation_code": code,
        "summary": "Deterministic policy evaluation only; no model interpretation.",
        "evidence": list(policy.evidence),
        "required_approvals": list(policy.required_approvals),
        "missing_information": list(policy.missing_information),
        "risk_flags": list(policy.risk_flags),
        "next_step": default_next_step(code, policy.required_approvals),
        "human_review_required": True,
    }
