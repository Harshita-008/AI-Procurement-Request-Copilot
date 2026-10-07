"""Architecture B: Procurement Analyst (tools) -> Policy/Risk Reviewer (no tools)."""
from __future__ import annotations

from src import prompts
from src.agents.loop import run_tool_loop
from src.agents.schemas import EvidencePack, ModelDecision
from src.llm import BaseLLM, LLMError
from src.tools.context import ToolContext


def run(llm: BaseLLM, ctx: ToolContext) -> tuple[ModelDecision, EvidencePack]:
    pack = run_tool_loop(
        llm, ctx,
        system=prompts.ANALYST,
        user_message=prompts.request_message(ctx.request),
        output_model=EvidencePack,
        label="analyst",
    )
    policy_result = ctx.call("run_policy_checks", internal=True)
    tool_results = {name: out for (name, _), out in ctx.cache.items() if name != "run_policy_checks"}

    # No tools for the reviewer; just retry once if its JSON is invalid.
    messages = [{"role": "user", "content": prompts.reviewer_message(ctx.request, pack.model_dump(), tool_results, policy_result)}]
    for _ in range(2):
        response = llm.structured(system=prompts.REVIEWER, messages=messages, output_model=ModelDecision, label="reviewer")
        if response.parsed is not None:
            return response.parsed, pack
        messages += llm.assistant_turn(response)
        messages.append({"role": "user", "content": f"Return only the final structured JSON answer now. Validation error: {response.parse_error}"})
    raise LLMError("reviewer: no structured answer")
