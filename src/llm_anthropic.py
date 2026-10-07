"""Claude via the Anthropic SDK: native tool use + schema-validated structured output."""
from __future__ import annotations

import time

import anthropic

from src.config import API_KEY, MAX_OUTPUT_TOKENS, MODEL_EFFORT, MODEL_NAME
from src.llm import BaseLLM, LLMError, LLMResponse, ToolCall


class AnthropicLLM(BaseLLM):
    def __init__(self, model: str = MODEL_NAME, effort: str = MODEL_EFFORT):
        if not API_KEY:
            raise LLMError("ANTHROPIC_API_KEY is not set")
        self.client = anthropic.Anthropic(api_key=API_KEY, max_retries=2, timeout=120.0)
        self.model = model
        self.effort = effort
        self.calls = []

    def structured(self, *, system, messages, output_model, tools=None, label="", force_tools=False):
        # force_tools is ignored: current Claude models reject forced tool_choice, so the prompt steers tool use
        # and the agent loop's completeness gate re-asks if a tool was skipped.
        started = time.perf_counter()
        request = {
            "model": self.model,
            "max_tokens": MAX_OUTPUT_TOKENS,
            "system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            "messages": messages,
            "tools": tools or anthropic.omit,
            "output_format": output_model,
        }
        if self.effort:  # optional: not every model accepts an effort setting
            request["output_config"] = {"effort": self.effort}
        try:
            response = self.client.messages.parse(**request)
        except anthropic.APIError as exc:
            raise LLMError(f"Claude API error: {exc}") from exc

        tool_calls = [ToolCall(b.id, b.name, dict(b.input)) for b in response.content if b.type == "tool_use"]
        self.calls.append({
            "type": "llm_call", "label": label, "model": self.model, "stop_reason": response.stop_reason,
            "tools_requested": [t.name for t in tool_calls],
            "input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens,
            "cache_read_input_tokens": response.usage.cache_read_input_tokens or 0,
            "duration_ms": round((time.perf_counter() - started) * 1000, 1),
        })
        if response.stop_reason == "refusal":
            raise LLMError("model refused the request")
        if response.stop_reason == "max_tokens":
            raise LLMError("model output was truncated")
        return LLMResponse(tool_calls=tool_calls, parsed=response.parsed_output, parse_error=None, raw=response)

    def assistant_turn(self, response):
        return [{"role": "assistant", "content": response.raw.content}]

    def tool_result_turn(self, results):
        blocks = [{"type": "tool_result", "tool_use_id": call.id, "content": text, "is_error": is_error}
                  for call, text, is_error in results]
        return [{"role": "user", "content": blocks}]
