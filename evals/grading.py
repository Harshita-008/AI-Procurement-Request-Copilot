"""Scoring helpers shared by the public runner and the architecture comparison."""
from __future__ import annotations

from src.contracts import ProcurementDecision
from src.data_access import get_request
from src.grounding import known_values, unverified_values

ENGINE_SOURCES = {"required_fields", "budget_check", "approval_thresholds", "catalog_overlap",
                  "vendor_status", "data_classification", "injection_scan"}


def norm(value: object) -> str:
    return str(value).strip().lower()


def group_present(items: list, group: list[str]) -> bool:
    texts = [norm(x) for x in items]
    return any(any(norm(token) in item for item in texts) for token in group)


def minimum_check_failures(decision: ProcurementDecision, expectations: dict) -> list[str]:
    """The starter pack's minimum behavioural expectations."""
    failures: list[str] = []
    for group in expectations.get("required_approvals_any_groups", []):
        if not group_present(decision.required_approvals, group):
            failures.append(f"approval missing (expected one of: {group})")
    for group in expectations.get("risk_flags_any_groups", []):
        if not group_present(decision.risk_flags, group):
            failures.append(f"risk flag missing (expected one of: {group})")
    for group in expectations.get("missing_information_any_groups", []):
        if not group_present(decision.missing_information, group):
            failures.append(f"missing-info item absent (expected one of: {group})")
    for token in expectations.get("risk_flags_must_not_contain", []):
        if group_present(decision.risk_flags, [token]):
            failures.append(f"unexpected risk flag containing: {token}")
    max_missing = expectations.get("max_missing_information")
    if max_missing is not None and len(decision.missing_information) > max_missing:
        failures.append(f"too many missing-information items: {len(decision.missing_information)} > {max_missing}")
    if len(decision.evidence) < expectations.get("min_evidence_items", 0):
        failures.append(f"insufficient evidence items: {len(decision.evidence)} < {expectations['min_evidence_items']}")
    expected_human = expectations.get("human_review_required")
    if expected_human is not None and decision.human_review_required != expected_human:
        failures.append(f"human_review_required expected {expected_human}")
    return failures


def escalation_correct(decision: ProcurementDecision, expectations: dict) -> bool:
    """Human review is required and every approver the case expects is routed."""
    groups = expectations.get("required_approvals_any_groups", [])
    return bool(decision.human_review_required) and all(group_present(decision.required_approvals, g) for g in groups)


def recommendation_correct(code: str | None, expectations: dict) -> bool | None:
    accepted = expectations.get("expected_recommendation_any")
    return None if not accepted else code in accepted


def raw_grounding_ratio(decision: ProcurementDecision) -> float | None:
    """Share of the model's own evidence items whose source is a tool that actually ran."""
    tel = decision.telemetry
    if not tel or not tel.raw_model_output:
        return None
    evidence = tel.raw_model_output.get("evidence", [])
    if not evidence:
        return 0.0
    allowed = set(tel.tool_names)  # only tools the agent itself called
    return sum(1 for e in evidence if e.get("source") in allowed) / len(evidence)


def raw_value_grounding_ratio(decision: ProcurementDecision) -> float | None:
    """Share of the model's evidence items whose quoted numbers all exist in data the model saw."""
    tel = decision.telemetry
    if not tel or not tel.raw_model_output:
        return None
    evidence = tel.raw_model_output.get("evidence", [])
    if not evidence:
        return 0.0
    seen = [t["output"] for t in tel.trace if t.get("type") == "tool_call" and not t.get("internal")]
    known = known_values(seen, get_request(decision.request_id))
    return sum(1 for e in evidence if not unverified_values(e.get("finding", ""), known)) / len(evidence)


def policy_corrections(decision: ProcurementDecision) -> int:
    """Guardrail corrections that changed approvals, flags or the recommendation."""
    tel = decision.telemetry
    if not tel:
        return 0
    keys = ("added approval", "added risk flag", "removed unsupported", "downgraded", "set to request_clarification")
    return sum(1 for c in tel.guardrail_corrections if any(k in c for k in keys))
