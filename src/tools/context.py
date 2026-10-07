"""Per-request tool context: caches tool results and records telemetry + trace."""
from __future__ import annotations

import inspect
import json
import time

from src.injection import scan_request
from src.request_normalize import normalize_request
from src.telemetry import RunTelemetryCounter


class ToolContext:
    def __init__(self, request: dict):
        self.request = normalize_request(request)
        self.request["_injection_hits"] = scan_request(self.request)
        self.cache: dict[tuple, dict] = {}
        self.telemetry = RunTelemetryCounter()
        self.trace: list[dict] = []

    def call(self, name: str, inputs: dict | None = None, internal: bool = False) -> dict:
        """Run a tool by name. Internal calls (tool-to-tool) are traced but not counted."""
        from src.tools.registry import TOOL_FUNCTIONS

        inputs = inputs or {}
        if name not in TOOL_FUNCTIONS:
            return {"error": f"unknown tool '{name}'"}
        accepted = set(inspect.signature(TOOL_FUNCTIONS[name]).parameters) - {"ctx"}
        ignored = sorted(set(inputs) - accepted)
        inputs = {k: v for k, v in inputs.items() if k in accepted}
        key = (name, json.dumps(inputs, sort_keys=True, default=str))
        started = time.perf_counter()
        cached = key in self.cache
        if not cached:
            try:
                self.cache[key] = TOOL_FUNCTIONS[name](self, **inputs)
            except TypeError as exc:
                self.cache[key] = {"error": f"bad arguments for {name}: {exc}"}
        if not internal:
            self.telemetry.record_tool_call(name)
        self.trace.append({
            "type": "tool_call",
            "tool": name,
            "inputs": inputs,
            "internal": internal,
            "cached": cached,
            "ignored_inputs": ignored,
            "duration_ms": round((time.perf_counter() - started) * 1000, 1),
            "output": self.cache[key],
        })
        return self.cache[key]

    def tools_used(self) -> set[str]:
        """Tools the agent itself called (internal tool-to-tool runs do not count as grounding)."""
        return {t["tool"] for t in self.trace if t["type"] == "tool_call" and not t["internal"]}
