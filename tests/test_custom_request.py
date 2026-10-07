"""Requests typed into the UI flow through the same pipeline as the sample data."""
from __future__ import annotations

import unittest
from unittest import mock

from src.pipeline import run
from ui.custom_request import integrations_from_text, optional_text

RISK = {"risk_level": "low", "security_review_status": "approved", "last_review_date": "2026-06-20",
        "processes_personal_data": False, "stores_data_outside_region": False, "notes": ""}


class FormHelpers(unittest.TestCase):
    def test_blank_means_not_provided(self):
        self.assertIsNone(optional_text("   "))
        self.assertIsNone(integrations_from_text(""))

    def test_none_means_no_integrations_needed(self):
        self.assertEqual(integrations_from_text("None"), [])

    def test_comma_list(self):
        self.assertEqual(integrations_from_text("SSO, CRM ,"), ["SSO", "CRM"])


class CustomRequestPipeline(unittest.TestCase):
    @mock.patch("src.tools.vendor.fetch_vendor_risk", return_value=(RISK, "ok", None))
    def test_rules_architecture_on_a_typed_request(self, _):
        request = {
            "request_id": "CUSTOM-001", "requester_id": "E004", "product_name": "Ledgerly", "vendor_name": "Ledgerly",
            "category": "Finance", "annual_cost_usd": "12,000", "user_count": "5",
            "business_justification": "Replace manual reconciliation.", "data_access_level": "customer_pii",
            "requested_integrations": None, "urgency": "normal",
        }
        decision = run(request, architecture="rules")
        self.assertEqual(decision.request_id, "CUSTOM-001")
        self.assertIn("privacy_review_required", decision.risk_flags)      # customer PII, from the text field
        self.assertIn("missing_information", decision.risk_flags)          # integrations field omitted
        self.assertEqual(decision.recommendation_code, "request_clarification")
        self.assertTrue(decision.human_review_required)


if __name__ == "__main__":
    unittest.main()
