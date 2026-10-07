from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    source: str = Field(description="Tool/data source name")
    finding: str = Field(description="Concise factual finding")
    reference: str | None = Field(default=None, description="Optional record ID / policy section / endpoint")


class RunTelemetry(BaseModel):
    llm_calls: int | None = None
    tool_calls: int | None = None
    tool_names: list[str] = Field(default_factory=list)
    # Extra observability fields (all optional, harness ignores them).
    architecture: str | None = None
    model: str | None = None
    latency_ms: float | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cache_read_input_tokens: int | None = None
    guardrail_corrections: list[str] = Field(default_factory=list)
    raw_model_output: dict | None = None
    trace: list[dict] = Field(default_factory=list)


class ProcurementDecision(BaseModel):
    request_id: str
    recommendation: str = Field(description="Short recommendation label or sentence")
    recommendation_code: str | None = None
    summary: str | None = None
    evidence: list[EvidenceItem] = Field(default_factory=list)
    required_approvals: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    next_step: str
    human_review_required: bool = True
    telemetry: RunTelemetry | None = None


Architecture = Literal["single", "staged", "rules"]

# Approval names: rules/engine.py APPROVAL_ORDER. Risk flags: recommendations.py KNOWN_FLAGS.
