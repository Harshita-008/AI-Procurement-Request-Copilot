"""Combine all deterministic rules into one PolicyResult."""
from __future__ import annotations

from pydantic import BaseModel, Field

from src.config import REFERENCE_DATE
from src.recommendations import label
from src.rules.budget import approval_tier, check_budget
from src.rules.data_class import classify_data_access
from src.rules.fields import check_required_fields
from src.rules.reviews import legal_reasons, privacy_reasons, security_reasons

APPROVAL_ORDER = ["Manager", "Department Head", "Procurement", "Finance", "CFO", "Security", "Privacy", "Legal"]


class PolicyResult(BaseModel):
    reference_date: str
    data_classes: dict
    missing_information: list[str]
    budget: dict
    approval_tier: dict
    required_approvals: list[str]
    risk_flags: list[str]
    reasons: dict[str, list[str]] = Field(default_factory=dict)
    suggested_recommendation_code: str
    suggested_recommendation: str
    evidence: list[dict]


def _sorted_approvals(approvals: set[str]) -> list[str]:
    return [a for a in APPROVAL_ORDER if a in approvals]


def _recommend(flags: set[str], missing: list[str], overlap: list[dict]) -> str:
    if missing:
        return "request_clarification"
    if flags & {"vendor_risk_unavailable", "conflicting_vendor_evidence", "prompt_injection_detected"}:
        return "escalate_manual_review"
    if "budget_insufficient" in flags:
        return "escalate_budget_exception"
    if flags & {"security_review_required", "privacy_review_required", "legal_review_required", "vendor_review_expired"}:
        return "route_for_reviews"
    if any(m["match_kind"] == "same_product" for m in overlap):
        return "evaluate_existing_tool_first"
    return "approve_with_standard_approvals"


def evaluate_policy(request: dict, requester: dict, catalog: dict, vendor: dict) -> PolicyResult:
    """requester / catalog / vendor are the outputs of the three gathering tools."""
    employee = requester.get("employee")
    budget_row = requester.get("budget") or {}
    cost = request.get("annual_cost_usd")
    data = classify_data_access(request.get("data_access_level"), request.get("requested_integrations"))
    assessment = vendor["assessment"]
    overlap = catalog.get("matches", [])
    injection = list(request.get("_injection_hits", [])) + vendor.get("untrusted_text_flags", [])

    flags: set[str] = set()
    reasons: dict[str, list[str]] = {}
    evidence: list[dict] = []

    def flag(name: str, why: list[str]) -> None:
        if why:
            flags.add(name)
            reasons[name] = why

    missing = check_required_fields(request, employee, data["known"])
    if "unclassified" in data["classes"]:
        missing.append(f"data-access level '{data['raw']}' could not be classified; confirm the data sensitivity")
    field_gaps = list(missing)
    flag("missing_information", missing)
    if missing:
        evidence.append({"source": "required_fields", "finding": "Missing: " + "; ".join(missing), "reference": "Policy §1"})

    budget = check_budget(cost, budget_row.get("available_usd"))
    if budget["status"] == "exceeds":
        flag("budget_insufficient", [f"cost ${cost:,.0f} exceeds available ${budget['available_usd']:,.0f}"])
    evidence.append({
        "source": "budget_check",
        "finding": f"Budget {budget['status']}: cost {cost if cost is not None else 'unknown'} vs available "
                   f"{budget['available_usd']} USD for {budget_row.get('department', 'unknown department')}",
        "reference": "Policy §2",
    })

    tier = approval_tier(cost)
    approvals = set(tier["approvals"])
    evidence.append({"source": "approval_thresholds", "finding": f"Amount tier {tier['tier']} requires {', '.join(tier['approvals'])}", "reference": "Policy §4"})

    if overlap:
        flag("existing_tool_overlap", [f"{m['product_name']} ({m['match_kind']}, {m['status']}, {m['scope']})" for m in overlap])
        evidence.append({"source": "catalog_overlap", "finding": "Existing catalog items: " + "; ".join(reasons["existing_tool_overlap"]), "reference": "Policy §3"})
    else:  # absence of overlap is a finding too
        evidence.append({"source": "catalog_overlap", "finding": "No approved catalog item matches this product, vendor or category", "reference": "Policy §3"})

    sec = security_reasons(data, assessment)
    flag("security_review_required", sec)
    if assessment["api_availability"] == "unavailable":  # outage: never infer a status (policy §5)
        flag("vendor_risk_unavailable", [f"vendor-risk service unavailable: {vendor['risk_service'].get('error')}"])
        missing.append("vendor security assessment status (vendor-risk service unavailable)")
    if assessment["assessment_expired"]:
        flag("vendor_review_expired", [f"last review {assessment['api_review_date']} is {assessment['days_since_api_review']} days before {REFERENCE_DATE}"])
    if assessment["conflict"]:
        flag("conflicting_vendor_evidence", assessment["conflict_reasons"])
    evidence.append({
        "source": "vendor_status",
        "finding": f"Registry: {assessment['registry_procurement_status']}/{assessment['registry_security_status']} "
                   f"({assessment['registry_review_date']}); risk service: {assessment['api_availability']}, "
                   f"status {assessment['api_security_status']} ({assessment['api_review_date']}); current={assessment['assessment_current']}",
        "reference": "Policy §5",
    })
    if sec:
        approvals.add("Security")

    priv = privacy_reasons(data, assessment)
    flag("privacy_review_required", priv)
    if priv:
        approvals.add("Privacy")

    legal = legal_reasons(cost, data, assessment)
    flag("legal_review_required", legal)
    if legal:
        approvals.add("Legal")

    evidence.append({"source": "data_classification", "finding": f"Data access '{data['raw']}' -> classes {data['classes'] or ['none']}, sensitive={data['sensitive']}", "reference": "Policy §5-6"})

    if injection:
        flag("prompt_injection_detected", [f"{h['source']}: '{h['snippet']}'" for h in injection])
        evidence.append({"source": "injection_scan", "finding": "Untrusted text tried to alter rules: " + "; ".join(reasons["prompt_injection_detected"]), "reference": "Policy §9"})

    if "budget_insufficient" in flags:
        approvals.add("Finance")

    code = _recommend(flags, field_gaps, overlap)
    return PolicyResult(
        reference_date=str(REFERENCE_DATE),
        data_classes=data,
        missing_information=missing,
        budget=budget,
        approval_tier=tier,
        required_approvals=_sorted_approvals(approvals),
        risk_flags=sorted(flags),
        reasons=reasons,
        suggested_recommendation_code=code,
        suggested_recommendation=label(code),
        evidence=evidence,
    )
