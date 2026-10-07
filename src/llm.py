"""Provider-neutral LLM interface. The provider comes from LLM_PROVIDER or the API key present (see config)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.config import LLM_SDK


class LLMError(RuntimeError):
    """Raised when the model cannot produce a usable answer (refusal, truncation, API failure)."""


@dataclass
class ToolCall:
    id: str
    name: str
    input: dict


@dataclass
class LLMResponse:
    tool_calls: list[ToolCall]
    parsed: Any | None          # validated output_model instance, when the model answered
    parse_error: str | None     # why the answer could not be validated, if it could not
    raw: Any                    # provider-native assistant message, replayed verbatim


class BaseLLM:
    """What the agents need from a provider. Subclasses live in llm_anthropic.py / llm_openai_compat.py."""

    model: str
    calls: list[dict]

    @property
    def call_count(self) -> int:
        return len(self.calls)

    def usage_totals(self) -> dict:
        keys = ("input_tokens", "output_tokens", "cache_read_input_tokens")
        return {k: sum(c[k] for c in self.calls) for k in keys}

    def structured(self, *, system: str, messages: list, output_model, tools: list | None = None,
                   label: str = "", force_tools: bool = False) -> LLMResponse:
        """force_tools asks the provider to require at least one tool call (ignored where unsupported)."""
        raise NotImplementedError

    def assistant_turn(self, response: LLMResponse) -> list[dict]:
        """Messages to append so the model sees its own previous turn."""
        raise NotImplementedError

    def tool_result_turn(self, results: list[tuple[ToolCall, str, bool]]) -> list[dict]:
        """Messages carrying (call, json_text, is_error) results back to the model."""
        raise NotImplementedError


def make_llm() -> BaseLLM:
    """Build the adapter for the configured provider (see config.PROVIDERS)."""
    if LLM_SDK == "anthropic":
        from src.llm_anthropic import AnthropicLLM
        return AnthropicLLM()
    from src.llm_openai_compat import OpenAICompatLLM
    return OpenAICompatLLM()
