"""Sidebar form for analysing a request that is not in the sample data."""
from __future__ import annotations

import streamlit as st

from src.data_access import load_employees

CUSTOM_REQUEST_ID = "CUSTOM-001"
URGENCY_OPTIONS = ("normal", "high", "urgent")
NO_INTEGRATIONS_WORDS = {"none", "no", "n/a", "-"}


def optional_text(value: str | None) -> str | None:
    """Blank means not provided. Numbers stay as text; the normaliser coerces them."""
    value = (value or "").strip()
    return value or None


def integrations_from_text(value: str | None) -> list[str] | None:
    """Blank = field omitted; 'none' = no integrations needed; otherwise a comma list."""
    text = (value or "").strip()
    if not text:
        return None
    if text.lower() in NO_INTEGRATIONS_WORDS:
        return []
    return [part.strip() for part in text.split(",") if part.strip()]


def request_form() -> dict:
    """Render the form and return a request shaped like data/requests.json."""
    employees = load_employees()
    labels = {e["employee_id"]: f"{e['employee_id']} · {e['name']} ({e['department']})" for e in employees}
    requester = st.selectbox("Requester", list(labels), format_func=labels.get, key="custom_requester")
    product = st.text_input("Product name", key="custom_product")
    vendor = st.text_input("Vendor name", key="custom_vendor", help="Any name. Unknown vendors are handled as a risk, not an error.")
    category = st.text_input("Category", key="custom_category")
    cost = st.text_input("Annual cost (USD)", key="custom_cost", help="Leave blank to test a request with no cost.")
    users = st.text_input("Users / seats", key="custom_users")
    data_level = st.text_input("Data access level", key="custom_data",
                               help="Free text, e.g. customer_pii, source_code, internal documents, none.")
    integrations = st.text_input("Integrations", key="custom_integrations",
                                 help="Comma-separated. Type 'none' for no integrations; leave blank to omit the field.")
    urgency = st.selectbox("Urgency", URGENCY_OPTIONS, key="custom_urgency")
    justification = st.text_area("Business justification", key="custom_justification", height=110)
    return {
        "request_id": CUSTOM_REQUEST_ID,
        "requester_id": requester,
        "product_name": optional_text(product),
        "vendor_name": optional_text(vendor),
        "category": optional_text(category),
        "annual_cost_usd": optional_text(cost),
        "user_count": optional_text(users),
        "business_justification": optional_text(justification),
        "data_access_level": optional_text(data_level),
        "requested_integrations": integrations_from_text(integrations),
        "urgency": urgency,
    }
