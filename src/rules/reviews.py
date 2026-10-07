"""Policy sections 5, 6, 7: Security, Privacy and Legal review triggers."""
from __future__ import annotations

LEGAL_SPEND_THRESHOLD = 10_000
STANDARD_LEGAL_TERMS = {"approved", "standard"}


def security_reasons(data: dict, vendor: dict) -> list[str]:
    reasons = []
    for cls in data["classes"]:
        if cls == "source_code":
            reasons.append("source code access")
        elif cls == "production_access":
            reasons.append("production or cloud-account integration")
        elif cls == "confidential_documents":
            reasons.append("confidential documents")
        elif cls in {"customer_pii", "employee_pii", "pii_unspecified"}:
            reasons.append(f"{cls.replace('_', ' ')} access")
        elif cls == "credentials":
            reasons.append("credentials/secrets access")
        elif cls == "unclassified":
            reasons.append(f"data-access level '{data['raw']}' is not a recognised class; treated as sensitive until confirmed")
    if vendor["api_availability"] != "ok":
        reasons.append("vendor security assessment could not be verified")
    elif not vendor["assessment_current"]:
        reasons.append("vendor security assessment is missing, expired or not completed")
    if vendor["conflict"]:
        reasons.append("internal registry and vendor-risk service disagree")
    return reasons


def privacy_reasons(data: dict, vendor: dict) -> list[str]:
    reasons = []
    if data["pii"]:
        reasons.append("tool will process employee or customer PII")
    if vendor.get("stores_data_outside_region") and data["sensitive"]:
        reasons.append("sensitive data may be stored outside the operating region")
    return reasons


def legal_reasons(cost: float | None, data: dict, vendor: dict) -> list[str]:
    reasons = []
    if vendor["is_new_vendor"] and cost is not None and cost >= LEGAL_SPEND_THRESHOLD:
        reasons.append(f"new vendor with annual spend >= ${LEGAL_SPEND_THRESHOLD:,}")
    terms = str(vendor.get("registry_legal_terms_status") or "").lower()
    if terms not in STANDARD_LEGAL_TERMS:
        reasons.append(f"legal terms not approved/standard (status: {terms or 'unknown'})")
    if vendor.get("stores_data_outside_region") and data["sensitive"]:
        reasons.append("cross-region data-processing issue")
    return reasons
