"""Policy section 5 (vendor part): assessment currency and registry vs. API conflicts."""
from __future__ import annotations

from datetime import date

from src.config import REFERENCE_DATE, REVIEW_VALID_DAYS

APPROVED_WORDS = {"approved", "current", "passed"}
NOT_APPROVED_WORDS = {"pending", "not_completed", "expired", "unknown", "failed", "rejected", ""}


def _norm(value) -> str:
    return str(value or "").strip().lower().replace(" ", "_")


def _parse_date(value) -> date | None:
    try:
        return date.fromisoformat(str(value)) if value else None
    except ValueError:
        return None


def _currency(review_date: date | None) -> dict:
    if review_date is None:
        return {"days_since_review": None, "current": False}
    days = (REFERENCE_DATE - review_date).days
    return {"days_since_review": days, "current": 0 <= days <= REVIEW_VALID_DAYS}


def assess_vendor(registry: dict | None, risk: dict | None, availability: str) -> dict:
    """Combine the internal registry row and the external risk record into one verdict.

    availability: "ok" | "unavailable" | "no_record"
    """
    reg_status = _norm(registry.get("security_status")) if registry else ""
    reg_date = _parse_date(registry.get("security_review_date")) if registry else None
    api_status = _norm(risk.get("security_review_status")) if risk else ""
    api_date = _parse_date(risk.get("last_review_date")) if risk else None

    reg_cur = _currency(reg_date)
    api_cur = _currency(api_date)

    conflicts: list[str] = []
    if registry and risk:
        reg_ok = reg_status in APPROVED_WORDS
        api_ok = api_status in APPROVED_WORDS
        if reg_ok != api_ok:
            conflicts.append(f"registry says '{reg_status}' but risk service says '{api_status}'")
        if reg_date and api_date and reg_date != api_date:
            conflicts.append(f"review dates differ ({reg_date} vs {api_date})")
    if registry and reg_status in APPROVED_WORDS and not reg_cur["current"]:
        conflicts.append(f"registry marks the vendor approved but its review date is outside the {REVIEW_VALID_DAYS}-day window")

    assessment_current = bool(
        availability == "ok" and api_status in APPROVED_WORDS and api_cur["current"]
    )
    is_new = not registry or _norm(registry.get("procurement_status")) != "approved"

    return {
        "is_new_vendor": is_new,
        "registry_procurement_status": registry.get("procurement_status") if registry else None,
        "registry_security_status": registry.get("security_status") if registry else None,
        "registry_review_date": str(reg_date) if reg_date else None,
        "registry_legal_terms_status": registry.get("legal_terms_status") if registry else None,
        "api_availability": availability,
        "api_security_status": risk.get("security_review_status") if risk else None,
        "api_review_date": str(api_date) if api_date else None,
        "api_risk_level": risk.get("risk_level") if risk else None,
        "processes_personal_data": risk.get("processes_personal_data") if risk else None,
        "stores_data_outside_region": risk.get("stores_data_outside_region") if risk else None,
        "days_since_api_review": api_cur["days_since_review"],
        "assessment_current": assessment_current,
        "assessment_expired": bool(api_date and not api_cur["current"]) or api_status == "expired",
        "conflict": bool(conflicts),
        "conflict_reasons": conflicts,
        "reference_date": str(REFERENCE_DATE),
    }
