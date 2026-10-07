from __future__ import annotations

import unittest

from src.guardrail import same_topic
from src.request_normalize import normalize_request


class NormalizeTests(unittest.TestCase):
    def test_numeric_strings_and_blank_values(self):
        req = normalize_request({"annual_cost_usd": "$12,000", "user_count": "", "product_name": "  X "})
        self.assertEqual(req["annual_cost_usd"], 12000)
        self.assertIsNone(req["user_count"])
        self.assertEqual(req["product_name"], "X")

    def test_integrations_as_string_become_list(self):
        req = normalize_request({"requested_integrations": "SSO, CRM"})
        self.assertEqual(req["requested_integrations"], ["SSO", "CRM"])

    def test_missing_integrations_stay_none(self):
        self.assertIsNone(normalize_request({})["requested_integrations"])

    def test_same_topic_merges_model_and_policy_wording(self):
        self.assertTrue(same_topic("user_count", "number of users/licenses"))
        self.assertTrue(same_topic("annual_cost_usd", "annual cost (or a reasonable annual estimate)"))
        self.assertFalse(same_topic("data_access_level", "business purpose"))


if __name__ == "__main__":
    unittest.main()
