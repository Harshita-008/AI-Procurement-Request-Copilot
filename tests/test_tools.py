from __future__ import annotations

import unittest
from unittest import mock

from src.data_access import get_request
from src.tools.context import ToolContext

RISK = {"risk_level": "low", "security_review_status": "approved", "last_review_date": "2026-06-20",
        "processes_personal_data": True, "stores_data_outside_region": False, "notes": "Current assessment."}


class ToolTests(unittest.TestCase):
    def test_requester_tool(self):
        ctx = ToolContext(get_request("REQ-1001"))
        out = ctx.call("get_requester_and_budget", {"requester_id": "E004"})
        self.assertEqual(out["employee"]["department"], "Finance")
        self.assertEqual(out["budget"]["available_usd"], 29000)
        self.assertEqual(ctx.telemetry.tool_calls, 1)

    def test_unknown_requester(self):
        ctx = ToolContext(get_request("REQ-1001"))
        self.assertFalse(ctx.call("get_requester_and_budget", {"requester_id": "E999"})["found"])

    def test_catalog_tool(self):
        ctx = ToolContext(get_request("REQ-1008"))
        out = ctx.call("search_software_catalog", {"product_name": "TaskFlow Pro", "vendor_name": "TaskFlow", "category": "Project Management"})
        self.assertEqual(out["matches"][0]["match_kind"], "same_product")
        self.assertEqual(len(out["purchase_history"]), 1)

    @mock.patch("src.tools.vendor.fetch_vendor_risk", return_value=(RISK, "ok", None))
    def test_vendor_tool_with_api(self, _):
        ctx = ToolContext(get_request("REQ-1001"))
        out = ctx.call("get_vendor_status", {"vendor_name": "SignFlow"})
        self.assertTrue(out["assessment"]["assessment_current"])

    @mock.patch("src.tools.vendor.fetch_vendor_risk", return_value=(None, "unavailable", "HTTP 503"))
    def test_policy_tool_counts_internal_calls_once(self, _):
        ctx = ToolContext(get_request("REQ-1009"))
        out = ctx.call("run_policy_checks")
        self.assertIn("vendor_risk_unavailable", out["risk_flags"])
        self.assertEqual(ctx.telemetry.tool_calls, 1)
        self.assertEqual(len(ctx.trace), 4)

    @mock.patch("src.tools.vendor.fetch_vendor_risk", return_value=(RISK, "ok", None))
    def test_junk_arguments_are_ignored(self, _):
        ctx = ToolContext(get_request("REQ-1001"))
        out = ctx.call("run_policy_checks", {"budget_check": "True"})
        self.assertIn("risk_flags", out)
        self.assertEqual(ctx.trace[-1]["ignored_inputs"], ["budget_check"])

    def test_cache_hits(self):
        ctx = ToolContext(get_request("REQ-1001"))
        ctx.call("get_requester_and_budget", {"requester_id": "E004"})
        ctx.call("get_requester_and_budget", {"requester_id": "E004"})
        self.assertTrue(ctx.trace[1]["cached"])

    def test_policy_lookup(self):
        ctx = ToolContext(get_request("REQ-1001"))
        out = ctx.call("lookup_policy", {"topics": ["privacy"]})
        self.assertTrue(any("Privacy" in s["title"] for s in out["sections"]))


if __name__ == "__main__":
    unittest.main()
