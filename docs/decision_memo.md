# Architecture Decision Memo

## Decision

Ship **Architecture A, the single agent**, on top of the deterministic policy engine and code guardrail. The staged variant scored the same and costs more.

## Evidence

Same 15 cases (6 public, 4 remaining starter requests, 5 synthetic hidden-style), three runs each, model `gemini-3.1-flash-lite`. Full table: `evals/results/comparison_summary.md`.

| Metric | Single agent | Staged / 2-agent | Rules only |
|---|---:|---:|---:|
| Cases passing minimum checks | 45/45 | 45/45 | 45/45 |
| Final recommendation correct | 45/45 | 45/45 | 45/45 |
| Escalation / human review correct | 45/45 | 45/45 | 45/45 |
| Model's own recommendation correct (pre-guardrail) | 44/45 | 43/45 | – |
| Evidence grounded: source / quoted values | 95% / 99% | 100% / 99% | – |
| Avg latency | 14.9 s | 20.2 s | 52 ms |
| Avg LLM calls / tool calls | 3.0 / 4.0 | 4.0 / 4.0 | 0 / 4.0 |
| Avg input + output tokens | 10.6k | 15.3k | 0 |

Each agent once ranked an existing-tool overlap above mandatory Security and Privacy reviews on the employee-PII case. The guardrail enforces that precedence, so final outputs were correct; the pre-guardrail row shows the miss.

An earlier single-agent run on a weaker free model (`nvidia/nemotron-3-super-120b-a12b:free`, archived under `evals/results/`) scored 7/15 before the guardrail and 13/15 after it. Model quality moved results far more than architecture did.

## Trade-offs

Staged improved one thing: source grounding reached 100%, because the reviewer sees only tool results and the analyst's pack. It cost an extra model call per request, 36% more latency, 44% more tokens, a second prompt to maintain and a hand-off where meaning can drift, and bought no accuracy.

The single agent is simpler to debug: one trace, one prompt, one output. Its 95% source grounding reflects occasional evidence citing a tool it had not called; the guardrail drops those items and fills the gap.

## Risks and limitations

- Fifteen cases (five self-written), three runs each, one free model; one case flipped between runs per agent. Enough to compare architectures, not to claim production accuracy.
- "Approve" versus "evaluate existing tool first" for add-ons is a judgment call the policy supports both ways. The expectation set should be agreed with Procurement.
- Grounding verifies source tools and quoted numbers, not the reasoning that links them.
- Data classification is keyword-based.

## Why this is the right MVP

The client needs evidence plus a defensible next step, with humans approving. Code decides thresholds, budget, expiry, required fields and injection, and the guardrail keeps the model's output no weaker than policy, so correctness does not depend on agent count. The model adds interpretation: whether a gap is credible, who acts next. One agent delivered that at the lowest cost and latency, with a trace a reviewer can read end to end. The rules-only baseline shows that the deterministic layer, not agent count, carries compliance.
