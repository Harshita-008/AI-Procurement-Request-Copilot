"""Reviewer actions are logged, never executed; an override records the reviewer's own recommendation."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ui import actions

DECISION = {"recommendation_code": "approve_with_standard_approvals", "required_approvals": ["Manager"]}


class ReviewLog(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patcher = mock.patch.object(actions, "LOG_PATH", Path(self.tmp.name) / "log.jsonl")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)

    def test_action_is_logged_and_filtered_by_request(self):
        actions.log_action("REQ-1", "single", "send_for_review", "Ana", "", DECISION)
        actions.log_action("REQ-2", "single", "return_to_requester", "", "dup", DECISION)
        entries = actions.load_actions("REQ-1")
        self.assertEqual([e["action"] for e in entries], ["send_for_review"])
        self.assertEqual(actions.load_actions("REQ-2")[0]["reviewer"], "anonymous")

    def test_override_keeps_both_recommendations(self):
        entry = actions.log_action("REQ-1", "single", actions.OVERRIDE_ACTION, "Ana", "Vendor is under investigation",
                                   DECISION, override_code="escalate_manual_review")
        self.assertEqual(entry["recommendation_code"], "approve_with_standard_approvals")
        self.assertEqual(entry["override_code"], "escalate_manual_review")
        self.assertEqual(actions.describe(entry), "Override recommendation → Escalate to manual review")


if __name__ == "__main__":
    unittest.main()
