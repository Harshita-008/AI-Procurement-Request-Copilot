"""The OpenAI-compatible adapter must keep working when an endpoint rejects optional features."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import httpx
import openai

from src.agents.schemas import ModelDecision


def _bad_request(message: str) -> openai.BadRequestError:
    response = httpx.Response(400, request=httpx.Request("POST", "http://x"), json={"error": {"message": message}})
    return openai.BadRequestError(message, response=response, body=None)


def _completion():
    message = MagicMock(content='{"recommendation_code": "route_for_reviews", "summary": "s", "evidence": [], '
                                '"required_approvals": [], "missing_information": [], "risk_flags": [], "next_step": "n"}',
                        tool_calls=None)
    return MagicMock(choices=[MagicMock(message=message, finish_reason="stop")], usage=None)


class FeatureDegradation(unittest.TestCase):
    def _llm(self):
        with patch.multiple("src.llm_openai_compat", API_KEY="k", API_BASE_URL="http://x", MODEL_NAME="m"):
            from src.llm_openai_compat import OpenAICompatLLM
            return OpenAICompatLLM(model="m")

    def test_forced_tool_choice_rejected(self):
        llm = self._llm()
        tools = [{"name": "t", "description": "d", "input_schema": {"type": "object", "properties": {}}}]
        llm.client.chat.completions.create = MagicMock(side_effect=[_bad_request("tool_choice unsupported"), _completion()])
        response = llm.structured(system="s", messages=[{"role": "user", "content": "u"}],
                                  output_model=ModelDecision, tools=tools, force_tools=True)
        self.assertEqual(response.parsed.recommendation_code, "route_for_reviews")
        self.assertEqual(llm.unsupported, {"tool_choice"})
        self.assertEqual(llm.client.chat.completions.create.call_count, 2)

    def test_strict_json_schema_rejected_then_parsed_from_text(self):
        llm = self._llm()
        llm.client.chat.completions.create = MagicMock(side_effect=[_bad_request("response_format unsupported"), _completion()])
        response = llm.structured(system="s", messages=[{"role": "user", "content": "u"}], output_model=ModelDecision)
        self.assertEqual(response.parsed.recommendation_code, "route_for_reviews")
        self.assertEqual(llm.unsupported, {"response_format"})
        # a feature the endpoint rejected is not requested again
        self.assertNotIn("response_format", llm.client.chat.completions.create.call_args.kwargs)

    def test_unrelated_bad_request_is_an_llm_error(self):
        from src.llm import LLMError
        llm = self._llm()
        llm.client.chat.completions.create = MagicMock(side_effect=_bad_request("model not found"))
        llm.unsupported = {"response_format"}
        with self.assertRaises(LLMError):
            llm.structured(system="s", messages=[{"role": "user", "content": "u"}], output_model=ModelDecision)

if __name__ == "__main__":
    unittest.main()
