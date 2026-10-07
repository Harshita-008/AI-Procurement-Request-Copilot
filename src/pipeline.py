"""Glue: request -> architecture -> guardrail -> ProcurementDecision with telemetry."""
from __future__ import annotations

import time

from src.agents import single, staged
from src.contracts import Architecture, ProcurementDecision, RunTelemetry
from src.grounding import known_values
from src.guardrail import apply_guardrail, rules_only_decision
from src.llm import LLMError, make_llm
from src.rules.engine import PolicyResult
from src.tools.context import ToolContext


def run(request: dict, architecture: Architecture = "single") -> ProcurementDecision:
    """Analyse one request record (sample, synthetic or typed into the UI) with the chosen architecture."""
    request_id = request["request_id"]
    ctx = ToolContext(request)
    llm = None
    started = time.perf_counter()
    corrections: list[str] = []
    draft = None
    extra_flags: list[str] = []

    if architecture in ("single", "staged"):
        try:
            llm = make_llm()
            draft = single.run(llm, ctx) if architecture == "single" else staged.run(llm, ctx)[0]
        except LLMError as exc:
            # Reliability control: if the model fails, fall back to rules and say so.
            corrections.append(f"model unavailable, deterministic fallback used: {exc}")
            extra_flags.append("llm_unavailable")

    policy = PolicyResult(**ctx.call("run_policy_checks", internal=True))
    if draft is not None:
        seen = [t["output"] for t in ctx.trace if t["type"] == "tool_call" and not t["internal"]]
        fields, guard_corrections = apply_guardrail(draft, policy, ctx.tools_used(), known_values(seen, ctx.request))
        corrections += guard_corrections
    else:
        fields = rules_only_decision(policy)
    fields["risk_flags"] = sorted(set(fields["risk_flags"]) | set(extra_flags))

    usage = llm.usage_totals() if llm else {"input_tokens": 0, "output_tokens": 0, "cache_read_input_tokens": 0}
    telemetry = RunTelemetry(
        llm_calls=llm.call_count if llm else 0,
        tool_calls=ctx.telemetry.tool_calls if architecture != "rules" else len(ctx.trace),
        tool_names=ctx.telemetry.tool_names if architecture != "rules" else [t["tool"] for t in ctx.trace],
        architecture=architecture,
        model=llm.model if llm else None,
        latency_ms=round((time.perf_counter() - started) * 1000, 1),
        guardrail_corrections=corrections,
        raw_model_output=draft.model_dump() if draft is not None else None,
        trace=ctx.trace + (llm.calls if llm else []),
        **usage,
    )
    return ProcurementDecision(request_id=request_id, telemetry=telemetry, **fields)
