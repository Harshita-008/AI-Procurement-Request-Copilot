"""Starter-pack public evaluation runner (kept CLI-compatible, extended with telemetry columns)."""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.grading import minimum_check_failures  # noqa: E402
from src.contracts import ProcurementDecision  # noqa: E402
from src.mock_api_runner import ensure_mock_api  # noqa: E402
from src.solution import handle_request  # noqa: E402


def run_case(case: dict, architecture: str) -> dict:
    start = time.perf_counter()
    row = {"case_id": case["case_id"], "request_id": case["request_id"], "architecture": architecture}
    try:
        raw = handle_request(case["request_id"], architecture=architecture)
        decision = raw if isinstance(raw, ProcurementDecision) else ProcurementDecision.model_validate(raw)
        failures = minimum_check_failures(decision, case["expectations"])
        tel = decision.telemetry
        row.update({
            "passed_minimum_checks": not failures,
            "latency_ms": round((time.perf_counter() - start) * 1000, 1),
            "llm_calls": tel.llm_calls if tel else "",
            "tool_calls": tel.tool_calls if tel else "",
            "model": tel.model if tel else "",
            "recommendation_code": decision.recommendation_code,
            "guardrail_corrections": len(tel.guardrail_corrections) if tel else "",
            "failures": " | ".join(failures),
        })
        print(f"{'PASS' if not failures else 'FAIL'}  {case['case_id']}  {case['title']}  ({row['latency_ms']:.0f} ms)")
        for failure in failures:
            print(f"      - {failure}")
    except Exception as exc:  # keep going so one broken case does not hide the others
        row.update({"passed_minimum_checks": False, "latency_ms": round((time.perf_counter() - start) * 1000, 1),
                    "llm_calls": "", "tool_calls": "", "model": "", "recommendation_code": "",
                    "guardrail_corrections": "", "failures": f"ERROR: {type(exc).__name__}: {exc}"})
        print(f"ERROR {case['case_id']}  {type(exc).__name__}: {exc}")
    return row


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--architecture", choices=["single", "staged", "rules"], default="single")
    args = parser.parse_args()

    cases = json.loads((ROOT / "evals" / "public_cases.json").read_text(encoding="utf-8"))
    print(f"\nPublic evaluation - architecture={args.architecture}\n")
    api_proc = ensure_mock_api()
    try:
        rows = [run_case(case, args.architecture) for case in cases]
    finally:
        if api_proc:
            api_proc.terminate()

    out_dir = ROOT / "evals" / "results"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / f"public_{args.architecture}.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    passed = sum(1 for r in rows if r["passed_minimum_checks"])
    print(f"\nMinimum checks passed: {passed}/{len(rows)}")
    print(f"Results written to: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
