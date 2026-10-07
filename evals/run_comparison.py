"""Run the same case set on every architecture and write a comparison report.

Every decision is saved under evals/results/decisions/ so runs can be resumed
(--resume skips saved cases) or re-scored without any model calls (--report-only).

Usage: python evals/run_comparison.py --architectures single staged rules --runs 1
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals import grading  # noqa: E402
from src import data_access  # noqa: E402
from src.agents.schemas import ModelDecision  # noqa: E402
from src.contracts import ProcurementDecision  # noqa: E402
from src.grounding import known_values  # noqa: E402
from src.guardrail import apply_guardrail  # noqa: E402
from src.rules.engine import PolicyResult  # noqa: E402
from src.tools.context import ToolContext  # noqa: E402
from src.mock_api_runner import ensure_mock_api  # noqa: E402
from src.solution import handle_request  # noqa: E402

RESULTS_DIR = ROOT / "evals" / "results"
DECISIONS_DIR = RESULTS_DIR / "decisions"

# USD per million tokens (input, output, cache read), matched by model-id prefix.
PRICES = {"claude-sonnet-5-5": (2.0, 10.0, 0.20), "claude-opus-5-5": (4.0, 20.0, 0.20), "claude-haiku-4-5": (1.0, 5.0, 0.10)}

COLUMNS = ["case_id", "request_id", "title", "architecture", "run", "model", "passed_minimum_checks", "recommendation_code",
           "recommendation_correct", "escalation_correct", "raw_recommendation_correct", "raw_grounding_ratio", "raw_value_grounding_ratio", "policy_corrections",
           "latency_ms", "llm_calls", "tool_calls", "input_tokens", "output_tokens", "cache_read_input_tokens",
           "cost_usd", "failures", "corrections"]


def include_synthetic_requests() -> None:
    """Let the pipeline resolve synthetic request ids without touching data/requests.json."""
    synthetic = json.loads((ROOT / "evals" / "synthetic_requests.json").read_text(encoding="utf-8"))
    original = data_access.load_requests
    data_access.load_requests = lambda: original() + synthetic


def cost_usd(model: str | None, usage: dict) -> float | None:
    if model and model.endswith(":free"):
        return 0.0
    for prefix, (inp, out, cache) in PRICES.items():
        if model and model.startswith(prefix):
            uncached = max(0, usage["input_tokens"] - usage["cache_read_input_tokens"])
            return round((uncached * inp + usage["output_tokens"] * out + usage["cache_read_input_tokens"] * cache) / 1e6, 5)
    return None


def decision_path(architecture: str, case_id: str, run: int) -> Path:
    return DECISIONS_DIR / architecture / f"{case_id}_run{run}.json"


def score(decision: ProcurementDecision, case: dict, architecture: str, run: int) -> dict:
    tel = decision.telemetry
    failures = grading.minimum_check_failures(decision, case["expectations"])
    raw_code = (tel.raw_model_output or {}).get("recommendation_code") if tel else None
    usage = {"input_tokens": tel.input_tokens or 0, "output_tokens": tel.output_tokens or 0,
             "cache_read_input_tokens": tel.cache_read_input_tokens or 0}
    return {
        "case_id": case["case_id"], "request_id": case["request_id"], "title": case["title"],
        "architecture": architecture, "run": run, "model": tel.model,
        "passed_minimum_checks": not failures,
        "recommendation_code": decision.recommendation_code,
        "recommendation_correct": grading.recommendation_correct(decision.recommendation_code, case["expectations"]),
        "escalation_correct": grading.escalation_correct(decision, case["expectations"]),
        "raw_recommendation_correct": grading.recommendation_correct(raw_code, case["expectations"]) if raw_code else None,
        "raw_grounding_ratio": grading.raw_grounding_ratio(decision),
        "raw_value_grounding_ratio": grading.raw_value_grounding_ratio(decision),
        "policy_corrections": grading.policy_corrections(decision),
        "latency_ms": tel.latency_ms, "llm_calls": tel.llm_calls, "tool_calls": tel.tool_calls,
        **usage, "cost_usd": cost_usd(tel.model, usage),
        "failures": " | ".join(failures), "corrections": " | ".join(tel.guardrail_corrections),
    }


def run_case(case: dict, architecture: str, run: int) -> dict:
    start = time.perf_counter()
    try:
        decision = handle_request(case["request_id"], architecture=architecture)
    except Exception as exc:
        return {"case_id": case["case_id"], "request_id": case["request_id"], "title": case["title"],
                "architecture": architecture, "run": run, "passed_minimum_checks": False,
                "latency_ms": round((time.perf_counter() - start) * 1000, 1), "failures": f"ERROR: {type(exc).__name__}: {exc}"}
    path = decision_path(architecture, case["case_id"], run)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(decision.model_dump_json(indent=1), encoding="utf-8")
    return score(decision, case, architecture, run)


def load_saved(case: dict, architecture: str, run: int, reguard: bool = False) -> dict | None:
    path = decision_path(architecture, case["case_id"], run)
    if not path.exists():
        return None
    decision = ProcurementDecision.model_validate_json(path.read_text(encoding="utf-8"))
    if reguard and decision.telemetry and decision.telemetry.raw_model_output:
        decision = reapply_guardrail(decision)
        path.write_text(decision.model_dump_json(indent=1), encoding="utf-8")
    return score(decision, case, architecture, run)


def reapply_guardrail(decision: ProcurementDecision) -> ProcurementDecision:
    """Re-run only the deterministic layer on a saved model draft (no model calls)."""
    tel = decision.telemetry
    ctx = ToolContext(data_access.get_request(decision.request_id))
    policy = PolicyResult(**ctx.call("run_policy_checks", internal=True))
    draft = ModelDecision.model_validate(tel.raw_model_output)
    seen = [t["output"] for t in tel.trace if t.get("type") == "tool_call" and not t.get("internal")]
    fields, corrections = apply_guardrail(draft, policy, set(tel.tool_names), known_values(seen, ctx.request))
    llm_notes = [c for c in tel.guardrail_corrections if c.startswith("model unavailable")]
    tel = tel.model_copy(update={"guardrail_corrections": llm_notes + corrections})
    return ProcurementDecision(request_id=decision.request_id, telemetry=tel, **fields)


def _mean(rows: list[dict], key: str, digits: int = 1) -> str:
    values = [r[key] for r in rows if isinstance(r.get(key), (int, float)) and not isinstance(r.get(key), bool)]
    return f"{statistics.mean(values):.{digits}f}" if values else "-"


def _rate(rows: list[dict], key: str) -> str:
    values = [r[key] for r in rows if r.get(key) is not None and r.get(key) != ""]
    return f"{sum(1 for v in values if v)}/{len(values)}" if values else "-"


def summary_markdown(rows: list[dict], architectures: list[str], case_count: int) -> str:
    by_arch = {a: [r for r in rows if r["architecture"] == a] for a in architectures}
    models = {a: sorted({str(r.get("model")) for r in by_arch[a] if r.get("model")}) for a in architectures}
    lines = ["# Architecture comparison\n", f"{case_count} cases. Runs per architecture: " +
             ", ".join(f"{a}={len({r['run'] for r in by_arch[a]})}" for a in architectures) + ".",
             "Models: " + ", ".join(f"{a}={'/'.join(models[a]) or 'none'}" for a in architectures) + "\n",
             "| Metric | " + " | ".join(architectures) + " |", "|---|" + "---:|" * len(architectures)]
    metrics = [
        ("Cases passing minimum checks", lambda rs: _rate(rs, "passed_minimum_checks")),
        ("Final recommendation correct", lambda rs: _rate(rs, "recommendation_correct")),
        ("Escalation / human review correct", lambda rs: _rate(rs, "escalation_correct")),
        ("Model's own recommendation correct (pre-guardrail)", lambda rs: _rate(rs, "raw_recommendation_correct")),
        ("Model evidence grounded in tool results (source)", lambda rs: _mean(rs, "raw_grounding_ratio", 2)),
        ("Model evidence values verified against tool results", lambda rs: _mean(rs, "raw_value_grounding_ratio", 2)),
        ("Policy corrections needed per case", lambda rs: _mean(rs, "policy_corrections", 2)),
        ("Avg latency (ms)", lambda rs: _mean(rs, "latency_ms", 0)),
        ("Avg LLM calls", lambda rs: _mean(rs, "llm_calls", 2)),
        ("Avg tool calls", lambda rs: _mean(rs, "tool_calls", 2)),
        ("Avg input tokens", lambda rs: _mean(rs, "input_tokens", 0)),
        ("Avg output tokens", lambda rs: _mean(rs, "output_tokens", 0)),
        ("Avg cost per case (USD)", lambda rs: _mean(rs, "cost_usd", 4)),
    ]
    for name, fn in metrics:
        lines.append(f"| {name} | " + " | ".join(fn(by_arch[a]) for a in architectures) + " |")

    lines += ["\n## Per case (final recommendation correct / minimum checks)\n",
              "| Case | Title | " + " | ".join(architectures) + " |", "|---|---|" + "---|" * len(architectures)]
    for case_id in dict.fromkeys(r["case_id"] for r in rows):
        cells = []
        for a in architectures:
            rs = [r for r in rows if r["case_id"] == case_id and r["architecture"] == a]
            cells.append(f"{_rate(rs, 'recommendation_correct')} / {_rate(rs, 'passed_minimum_checks')}")
        title = next(r["title"] for r in rows if r["case_id"] == case_id)
        lines.append(f"| {case_id} | {title} | " + " | ".join(cells) + " |")

    failures = [r for r in rows if r.get("failures")]
    if failures:
        lines.append("\n## Failures\n")
        lines += [f"- {r['architecture']} run {r['run']} {r['case_id']}: {r['failures']}" for r in failures]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--architectures", nargs="+", default=["single", "staged", "rules"])
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--cases", default="evals/extended_cases.json")
    parser.add_argument("--only", nargs="*", help="case ids to run (default all)")
    parser.add_argument("--resume", action="store_true", help="skip cases that already have a saved decision")
    parser.add_argument("--report-only", action="store_true", help="score saved decisions only, no model calls")
    parser.add_argument("--reguard", action="store_true", help="with saved decisions: re-apply the current guardrail to the stored model draft")
    args = parser.parse_args()

    cases = json.loads((ROOT / args.cases).read_text(encoding="utf-8"))
    if args.only:
        cases = [c for c in cases if c["case_id"] in args.only]
    include_synthetic_requests()
    RESULTS_DIR.mkdir(exist_ok=True)

    rows: list[dict] = []
    api_proc = None if (args.report_only and not args.reguard) else ensure_mock_api()  # reguard recomputes policy via the tools
    try:
        for architecture in args.architectures:
            for run in range(1, args.runs + 1):
                print(f"\n== {architecture} run {run}")
                for case in cases:
                    saved = load_saved(case, architecture, run, args.reguard) if (args.resume or args.report_only) else None
                    if saved is None and args.report_only:
                        continue
                    row = saved or run_case(case, architecture, run)
                    rows.append(row)
                    status = "PASS" if row.get("passed_minimum_checks") else "FAIL"
                    reco = "ok" if row.get("recommendation_correct") else "x"
                    tag = "(saved)" if saved else ""
                    print(f"{status} reco={reco} {row['case_id']:7} {row.get('recommendation_code', '')!s:32} "
                          f"{row.get('latency_ms') or 0:>7.0f} ms  llm={row.get('llm_calls', '-')} tools={row.get('tool_calls', '-')} {tag} {row.get('failures', '')}")
    finally:
        if api_proc:
            api_proc.terminate()

    if not rows:
        print("No results.")
        return
    with (RESULTS_DIR / "comparison_runs.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    summary = summary_markdown(rows, args.architectures, len(cases))
    (RESULTS_DIR / "comparison_summary.md").write_text(summary, encoding="utf-8")
    print("\n" + summary)
    print(f"Written: {RESULTS_DIR.relative_to(ROOT)}/comparison_runs.csv, comparison_summary.md and decisions/")


if __name__ == "__main__":
    main()
