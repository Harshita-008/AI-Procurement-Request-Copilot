from __future__ import annotations

import unittest

from src.agents.schemas import EvidenceOut, ModelDecision
from src.guardrail import apply_guardrail, normalize_approval
from src.rules.engine import PolicyResult


def policy(**overrides) -> PolicyResult:
    base = dict(
        reference_date="2026-09-30", data_classes={}, missing_information=[], budget={"status": "within"},
        approval_tier={}, required_approvals=["Department Head", "Procurement", "Security"],
        risk_flags=["security_review_required"], reasons={},
        suggested_recommendation_code="route_for_reviews", suggested_recommendation="Route",
        evidence=[{"source": "budget_check", "finding": "ok", "reference": "Policy §2"}],
    )
    return PolicyResult(**{**base, **overrides})


def draft(**overrides) -> ModelDecision:
    base = dict(
        recommendation_code="approve_with_standard_approvals", summary="fine",
        evidence=[EvidenceOut(source="get_vendor_status", finding="approved", reference="")],
        required_approvals=["dept head"], missing_information=[], risk_flags=["budget_insufficient"],
        next_step="approve",
    )
    return ModelDecision(**{**base, **overrides})


class GuardrailTests(unittest.TestCase):
    def test_adds_missing_approvals_and_flags(self):
        fields, corrections = apply_guardrail(draft(), policy(), {"get_vendor_status"})
        self.assertEqual(fields["required_approvals"], ["Department Head", "Procurement", "Security"])
        self.assertIn("security_review_required", fields["risk_flags"])
        self.assertTrue(any("added approval: Procurement" in c for c in corrections))

    def test_removes_code_owned_flag_the_model_invented(self):
        fields, corrections = apply_guardrail(draft(), policy(), {"get_vendor_status"})
        self.assertNotIn("budget_insufficient", fields["risk_flags"])
        self.assertTrue(any("removed unsupported risk flag" in c for c in corrections))

    def test_blocks_approve_when_reviews_required(self):
        fields, _ = apply_guardrail(draft(), policy(), {"get_vendor_status"})
        self.assertEqual(fields["recommendation_code"], "route_for_reviews")

    def test_drops_ungrounded_evidence_and_fills_gaps(self):
        d = draft(evidence=[EvidenceOut(source="my_memory", finding="x", reference="")])
        fields, corrections = apply_guardrail(d, policy(), {"get_vendor_status"})
        self.assertEqual([e["source"] for e in fields["evidence"]], ["budget_check"])
        self.assertTrue(any("ungrounded" in c for c in corrections))
        self.assertTrue(any("added deterministic evidence" in c for c in corrections))

    def test_covered_evidence_is_not_duplicated(self):
        d = draft(evidence=[EvidenceOut(source="get_requester_and_budget", finding="budget ok", reference="")])
        fields, _ = apply_guardrail(d, policy(), {"get_requester_and_budget"})
        self.assertEqual([e["source"] for e in fields["evidence"]], ["get_requester_and_budget"])

    def test_model_added_missing_info_is_dropped_when_request_complete(self):
        fields, corrections = apply_guardrail(draft(missing_information=["vendor SLA document"]), policy(), {"get_vendor_status"})
        self.assertEqual(fields["missing_information"], [])
        self.assertTrue(any("dropped model-added" in c for c in corrections))

    def test_material_missing_forces_clarification(self):
        p = policy(missing_information=["annual cost"], suggested_recommendation_code="request_clarification")
        fields, _ = apply_guardrail(draft(recommendation_code="route_for_reviews"), p, {"get_vendor_status"})
        self.assertEqual(fields["recommendation_code"], "request_clarification")
        self.assertIn("annual cost", fields["missing_information"])

    def test_mandatory_reviews_outrank_overlap_evaluation(self):
        fields, corrections = apply_guardrail(
            draft(recommendation_code="evaluate_existing_tool_first", risk_flags=["existing_tool_overlap", "privacy_review_required"]),
            policy(risk_flags=["existing_tool_overlap", "security_review_required", "privacy_review_required"]), {"get_vendor_status"})
        self.assertEqual(fields["recommendation_code"], "route_for_reviews")
        self.assertTrue(any("outrank" in c for c in corrections))

    def test_overlap_evaluation_stands_when_no_review_is_required(self):
        fields, _ = apply_guardrail(
            draft(recommendation_code="evaluate_existing_tool_first", risk_flags=["existing_tool_overlap"]),
            policy(risk_flags=["existing_tool_overlap"], required_approvals=["Department Head", "Procurement"],
                   suggested_recommendation_code="evaluate_existing_tool_first"), {"get_vendor_status"})
        self.assertEqual(fields["recommendation_code"], "evaluate_existing_tool_first")

    def test_human_review_always_true(self):
        fields, _ = apply_guardrail(draft(), policy(), {"get_vendor_status"})
        self.assertTrue(fields["human_review_required"])

    def test_drops_free_text_flags(self):
        d = draft(risk_flags=["budget_insufficient? no, budget sufficient", "security_review_required"])
        fields, corrections = apply_guardrail(d, policy(), {"get_vendor_status"})
        self.assertEqual(fields["risk_flags"], ["security_review_required"])
        self.assertTrue(any("non-taxonomy" in c for c in corrections))

    def test_budget_breach_forces_exception_route(self):
        p = policy(risk_flags=["budget_insufficient"], required_approvals=["Department Head", "Finance", "Procurement"],
                   suggested_recommendation_code="escalate_budget_exception")
        fields, _ = apply_guardrail(draft(recommendation_code="evaluate_existing_tool_first", risk_flags=[]), p, {"get_vendor_status"})
        self.assertEqual(fields["recommendation_code"], "escalate_budget_exception")

    def test_unverifiable_values_are_dropped(self):
        d = draft(evidence=[EvidenceOut(source="get_vendor_status", finding="budget $5,000 available", reference=""),
                            EvidenceOut(source="get_vendor_status", finding="reviewed 2026-06-20", reference="")])
        fields, corrections = apply_guardrail(d, policy(), {"get_vendor_status"}, known={"2026", "6", "20"})
        self.assertEqual([e["finding"] for e in fields["evidence"] if e["source"] == "get_vendor_status"], ["reviewed 2026-06-20"])
        self.assertTrue(any("values not in any tool result" in c for c in corrections))

    def test_alias_normalisation(self):
        self.assertEqual(normalize_approval("Head of Department"), "Department Head")
        self.assertEqual(normalize_approval("IT Security team"), "Security")


if __name__ == "__main__":
    unittest.main()
