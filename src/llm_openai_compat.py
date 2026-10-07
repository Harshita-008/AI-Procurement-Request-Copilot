"""Any OpenAI-compatible endpoint (OpenAI, Gemini, OpenRouter, ...).

Optional request features are dropped one at a time if the endpoint rejects them.
"""
from __future__ import annotations

import json
import re
import time

import openai
from pydantic import ValidationError

from src.config import API_BASE_URL, API_KEY, FORMAT_WITH_TOOLS, LLM_PROVIDER, MAX_OUTPUT_TOKENS, MODEL_NAME
from src.llm import BaseLLM, LLMError, LLMResponse, ToolCall

RATE_LIMIT_ATTEMPTS = 3
RATE_LIMIT_WAIT_SECONDS = 35
# Optional request features, in the order they are dropped if the endpoint returns 400.
OPTIONAL_FEATURES = ("tool_choice", "response_format")


def strict_schema(output_model) -> dict:
    """Pydantic schema with every object closed and fully required, as strict JSON mode demands."""
    schema = output_model.model_json_schema()

    def close(node):
        if isinstance(node, dict):
            if node.get("type") == "object" and "properties" in node:
                node["additionalProperties"] = False
                node["required"] = list(node["properties"])
            for value in node.values():
                close(value)
        elif isinstance(node, list):
            for value in node:
                close(value)

    close(schema)
    return schema


def to_openai_tools(tools: list[dict]) -> list[dict]:
    return [{"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["input_schema"]}}
            for t in tools]


def extract_json(text: str) -> str:
    """Pull the JSON object out of a reply that may be fenced or wrapped in prose."""
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        return fenced.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    return text[start:end + 1] if start >= 0 and end > start else text


class OpenAICompatLLM(BaseLLM):
    def __init__(self, model: str = MODEL_NAME):
        if not API_KEY or not API_BASE_URL or not model:
            raise LLMError(f"provider '{LLM_PROVIDER}' needs an API key, a base URL and MODEL_NAME")
        self.client = openai.OpenAI(base_url=API_BASE_URL, api_key=API_KEY, max_retries=4, timeout=120.0)
        self.model = model
        self.calls = []
        self.unsupported: set[str] = set()  # features this endpoint has rejected; not sent again

    def structured(self, *, system, messages, output_model, tools=None, label="", force_tools=False):
        started = time.perf_counter()
        request = self._build_request(system, messages, output_model, tools, force_tools)
        completion = self._create(request)
        if not completion.choices:
            raise LLMError(f"empty response from provider: {getattr(completion, 'error', None)}")

        choice = completion.choices[0]
        message = choice.message
        tool_calls = [self._tool_call(tc) for tc in message.tool_calls or []]
        parsed, parse_error = None, None
        if not tool_calls and message.content:
            try:
                parsed = output_model.model_validate_json(extract_json(message.content))
            except (ValidationError, ValueError) as exc:
                parse_error = str(exc)[:500]

        self._record(label, choice, tool_calls, completion.usage, started)
        if choice.finish_reason == "length":
            raise LLMError("model output was truncated")
        if choice.finish_reason == "content_filter":
            raise LLMError("model refused the request")
        return LLMResponse(tool_calls=tool_calls, parsed=parsed, parse_error=parse_error, raw=message)

    def _build_request(self, system, messages, output_model, tools, force_tools) -> dict:
        request = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}] + messages,
            "max_tokens": MAX_OUTPUT_TOKENS,
            "response_format": {"type": "json_schema", "json_schema": {
                "name": output_model.__name__, "strict": True, "schema": strict_schema(output_model)}},
        }
        if LLM_PROVIDER == "openrouter":  # route only to backends that honour tools + response_format
            request["extra_body"] = {"provider": {"require_parameters": True}}
        if tools:
            request["tools"] = to_openai_tools(tools)
            if force_tools:
                request["tool_choice"] = "required"
            if force_tools or not FORMAT_WITH_TOOLS:
                request.pop("response_format")  # the answer is parsed from text or formatted in a later call
        for feature in self.unsupported:
            request.pop(feature, None)
        return request

    def _create(self, request: dict):
        """Call the endpoint; wait out free-tier rate limits and drop features the endpoint rejects."""
        rate_limit_hits = 0
        while True:
            try:
                return self.client.chat.completions.create(**request)
            except openai.RateLimitError as exc:
                rate_limit_hits += 1
                if rate_limit_hits >= RATE_LIMIT_ATTEMPTS:
                    raise LLMError(f"{LLM_PROVIDER} rate limit: {exc}") from exc
                time.sleep(RATE_LIMIT_WAIT_SECONDS)
            except openai.BadRequestError as exc:
                feature = next((f for f in OPTIONAL_FEATURES if f in request), None)
                if feature is None:
                    raise LLMError(f"{LLM_PROVIDER} rejected the request: {exc}") from exc
                self.unsupported.add(feature)
                request.pop(feature)
                self.calls.append({"type": "note", "label": "feature_dropped", "feature": feature, "detail": str(exc)[:200]})
            except openai.APIError as exc:
                raise LLMError(f"{LLM_PROVIDER} API error: {exc}") from exc

    @staticmethod
    def _tool_call(tc) -> ToolCall:
        try:
            args = json.loads(tc.function.arguments or "{}")
        except json.JSONDecodeError:
            args = {"error": f"unparseable arguments: {tc.function.arguments}"}
        return ToolCall(tc.id, tc.function.name, args)

    def _record(self, label, choice, tool_calls, usage, started) -> None:
        details = getattr(usage, "prompt_tokens_details", None) if usage else None
        self.calls.append({
            "type": "llm_call", "label": label, "model": self.model, "stop_reason": choice.finish_reason,
            "tools_requested": [t.name for t in tool_calls],
            "input_tokens": usage.prompt_tokens if usage else 0, "output_tokens": usage.completion_tokens if usage else 0,
            "cache_read_input_tokens": (getattr(details, "cached_tokens", 0) or 0) if details else 0,
            "duration_ms": round((time.perf_counter() - started) * 1000, 1),
        })

    def assistant_turn(self, response):
        msg = response.raw
        turn = {"role": "assistant", "content": msg.content or ""}
        if msg.tool_calls:
            # Replay verbatim: some providers (Gemini) attach fields that must be echoed back.
            turn["tool_calls"] = [tc.model_dump(exclude_none=True) for tc in msg.tool_calls]
        return [turn]

    def tool_result_turn(self, results):
        return [{"role": "tool", "tool_call_id": call.id, "content": text} for call, text, _ in results]
