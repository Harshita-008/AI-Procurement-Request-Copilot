"""Classify the request's data-access level and integrations into policy data classes."""
from __future__ import annotations

SENSITIVE_CLASSES = {
    "customer_pii",
    "employee_pii",
    "source_code",
    "production_access",
    "confidential_documents",
    "credentials",
}

UNKNOWN_VALUES = {"", "unknown", "unspecified", "tbd", "n/a", "na", "not sure"}
# Words that mark a low-sensitivity class. Anything recognised by neither list is "unclassified".
INTERNAL_WORDS = ("internal", "public", "marketing", "general", "aggregate", "anonymi", "non sensitive", "low")

# (keywords that must all appear, resulting class)
_KEYWORD_RULES = [
    (("customer", "pii"), "customer_pii"),
    (("customer", "personal"), "customer_pii"),
    (("customer", "data"), "customer_pii"),
    (("employee", "pii"), "employee_pii"),
    (("employee", "personal"), "employee_pii"),
    (("hr", "data"), "employee_pii"),
    (("pii",), "pii_unspecified"),
    (("personal",), "pii_unspecified"),
    (("source",), "source_code"),
    (("code",), "source_code"),
    (("git",), "source_code"),
    (("codebase",), "source_code"),
    (("production",), "production_access"),
    (("prod",), "production_access"),
    (("cloud", "account"), "production_access"),
    (("confidential",), "confidential_documents"),
    (("contract",), "confidential_documents"),
    (("legal",), "confidential_documents"),
    (("financial",), "confidential_documents"),
    (("credential",), "credentials"),
    (("secret",), "credentials"),
    (("token",), "credentials"),
    (("api key",), "credentials"),
]


def _classes_in(text: str) -> set[str]:
    text = text.lower().replace("_", " ").replace("-", " ")
    found = set()
    for keywords, cls in _KEYWORD_RULES:
        if all(k in text for k in keywords):
            found.add(cls)
    if "pii_unspecified" in found and found & {"customer_pii", "employee_pii"}:
        found.discard("pii_unspecified")
    return found


def classify_data_access(level: str | None, integrations: list[str] | None = None) -> dict:
    """Return the known-ness and policy data classes for a request."""
    raw = (level or "").strip()
    known = raw.lower() not in UNKNOWN_VALUES
    classes: set[str] = set()
    if known:
        if raw.lower() in {"none", "no data"}:
            classes.add("none")
        else:
            lowered = raw.lower().replace("_", " ").replace("-", " ")
            classes |= _classes_in(raw) or ({"internal"} if any(w in lowered for w in INTERNAL_WORDS) else {"unclassified"})
    for item in integrations or []:
        classes |= _classes_in(item)
    if classes - {"internal"}:
        classes.discard("internal")
    return {
        "raw": raw or None,
        "known": known,
        "classes": sorted(classes),
        "sensitive": bool(classes & SENSITIVE_CLASSES or classes & {"pii_unspecified", "unclassified"}),
        "pii": bool(classes & {"customer_pii", "employee_pii", "pii_unspecified"}),
    }
