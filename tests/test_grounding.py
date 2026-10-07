from __future__ import annotations

import unittest

from src.grounding import known_values, numbers_in, unverified_values


class GroundingTests(unittest.TestCase):
    def test_numbers_normalise(self):
        self.assertEqual(numbers_in("$29,000 vs 29000.0 and 800"), {"29000", "800"})
        self.assertEqual(numbers_in("above $25k, 1.5M rows"), {"25000", "1.5e+06"})

    def test_known_values_include_tools_request_and_policy(self):
        known = known_values([{"budget": {"available_usd": 29000}}], {"annual_cost_usd": 800})
        self.assertTrue({"29000", "800", "365", "10000"} <= known)

    def test_unverified(self):
        self.assertEqual(unverified_values("budget $5,000, cost 800", {"800"}), ["5000"])


if __name__ == "__main__":
    unittest.main()
