"""Architecture A: one agent gathers evidence with tools and drafts the decision."""
from __future__ import annotations

from src import prompts
from src.agents.loop import run_tool_loop
from src.agents.schemas import ModelDecision
from src.llm import BaseLLM
from src.tools.context import ToolContext


def run(llm: BaseLLM, ctx: ToolContext) -> ModelDecision:
    return run_tool_loop(
        llm, ctx,
        system=prompts.SINGLE_AGENT,
        user_message=prompts.request_message(ctx.request),
        output_model=ModelDecision,
        label="single_agent",
    )
