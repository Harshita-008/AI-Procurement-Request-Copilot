"""Shared tool-use loop: model -> tools -> model until a structured answer arrives."""
from __future__ import annotations

import json

from src.config import MAX_AGENT_TURNS
from src.llm import BaseLLM, LLMError
from src.tools.context import ToolContext
from src.tools.registry import REQUIRED_TOOLS, TOOL_SPECS


def run_tool_loop(llm: BaseLLM, ctx: ToolContext, *, system: str, user_message: str, output_model, label: str):
    messages = [{"role": "user", "content": user_message}]
    force_tools = True
    for _ in range(MAX_AGENT_TURNS):
        response = llm.structured(system=system, messages=messages, output_model=output_model, tools=TOOL_SPECS,
                                  label=label, force_tools=force_tools)
        force_tools = False

        if response.tool_calls:
            messages += llm.assistant_turn(response)
            results = []
            for call in response.tool_calls:
                output = ctx.call(call.name, call.input)
                results.append((call, json.dumps(output, default=str), bool(output.get("error"))))
            messages += llm.tool_result_turn(results)
            continue

        if response.parsed is None:
            # Text that is not valid JSON: one formatting call with the schema and no tools.
            messages += llm.assistant_turn(response)
            problem = f" Validation error: {response.parse_error}" if response.parse_error else ""
            messages.append({"role": "user", "content": f"Return only the final structured JSON answer now.{problem}"})
            response = llm.structured(system=system, messages=messages, output_model=output_model, label=f"{label}_format")
            if response.parsed is None:
                continue

        missing_tools = REQUIRED_TOOLS - ctx.tools_used()
        if not missing_tools:
            return response.parsed
        # Completeness gate: no decision without the core evidence. Ask for the missing tools.
        messages += llm.assistant_turn(response)
        messages.append({"role": "user", "content": "Your answer is not accepted yet: you have not called "
                         + ", ".join(sorted(missing_tools)) + ". Call them now (all at once), then answer."})
        force_tools = True

    raise LLMError(f"{label}: no structured answer within {MAX_AGENT_TURNS} turns")
