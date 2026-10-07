"""Tool registry: JSON schemas for the model plus the Python functions behind them."""
from __future__ import annotations

from src.tools.catalog import search_software_catalog
from src.tools.policy import lookup_policy, run_policy_checks
from src.tools.requester import get_requester_and_budget
from src.tools.vendor import get_vendor_status

# Tools an agent must consult before its answer is accepted (reliability gate in agents/loop.py).
REQUIRED_TOOLS = {"get_requester_and_budget", "search_software_catalog", "get_vendor_status", "run_policy_checks"}

TOOL_FUNCTIONS = {
    "get_requester_and_budget": get_requester_and_budget,
    "search_software_catalog": search_software_catalog,
    "get_vendor_status": get_vendor_status,
    "run_policy_checks": run_policy_checks,
    "lookup_policy": lookup_policy,
}

# All five are deterministic (data lookups, an HTTP call, and pure rules). None call an LLM.
TOOL_SPECS = [
    {
        "name": "get_requester_and_budget",
        "description": "Look up the requesting employee, their manager, department and the department's available software budget.",
        "input_schema": {
            "type": "object",
            "properties": {"requester_id": {"type": "string", "description": "The request's requester_id"}},
            "required": ["requester_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "search_software_catalog",
        "description": "Find approved catalog software that overlaps with the request (same product, vendor or category) and prior purchases from the vendor.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_name": {"type": "string"},
                "vendor_name": {"type": "string"},
                "category": {"type": "string"},
            },
            "required": ["product_name", "vendor_name", "category"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_vendor_status",
        "description": "Get the vendor's internal registry record and the external vendor-risk service record, with assessment currency (365-day rule) and registry/API conflicts computed against the policy reference date.",
        "input_schema": {
            "type": "object",
            "properties": {"vendor_name": {"type": "string"}},
            "required": ["vendor_name"],
            "additionalProperties": False,
        },
    },
    {
        "name": "run_policy_checks",
        "description": "Deterministic policy engine: required fields, budget, approval thresholds, security/privacy/legal triggers, vendor currency, overlap and prompt-injection scan. Returns minimum approvals, risk flags and evidence with policy references.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "lookup_policy",
        "description": "Read procurement policy sections by number (e.g. '5') or keyword (e.g. 'privacy'). Omit topics to list all sections.",
        "input_schema": {
            "type": "object",
            "properties": {"topics": {"type": "array", "items": {"type": "string"}}},
            "additionalProperties": False,
        },
    },
]
