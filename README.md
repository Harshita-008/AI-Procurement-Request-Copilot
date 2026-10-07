# AI Procurement Request Copilot

[![ci](https://github.com/Harshita-008/AI-Procurement-Request-Copilot/actions/workflows/ci.yml/badge.svg)](https://github.com/Harshita-008/AI-Procurement-Request-Copilot/actions/workflows/ci.yml)

An internal copilot that reviews software purchase requests: it gathers evidence with tools, applies the procurement policy deterministically, and recommends the next action while every approval stays with a human.

**Design principle:** AI interprets and recommends · code enforces thresholds and checks · humans approve.

## Setup and run

Prerequisites: Python 3.11+ (tested on 3.13), a model API key (see below).

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
Copy-Item .env.example .env           # then add your key (see Model provider)
python verify_setup.py                # preflight: packages, data, contract, mock API
python run_local.py                   # one command: mock vendor-risk API :8001 + UI :8501
```

Open http://127.0.0.1:8501, pick a request, choose an architecture, click **Run analysis**.
The `rules` architecture and **Load saved evaluation result** work without any key.

Tests and evaluation:

```powershell
python -m unittest discover -s tests                     # 78 unit tests, no key needed
python evals/run_public_evals.py --architecture single   # starter's 6 public cases
python evals/run_public_evals.py --architecture staged
python evals/run_comparison.py --runs 3 --resume         # 15 cases x 3 runs on single, staged, rules
python evals/run_comparison.py --runs 3 --report-only --reguard   # re-apply guardrail to saved drafts, no model calls
```

GitHub Actions runs the key-free part on every push: preflight, unit tests, the rules-only public evaluation and a re-score of the saved decisions (`.github/workflows/ci.yml`).

### Model provider

Set **one** API key in `.env`; the provider is detected from it. `LLM_PROVIDER` is only needed when several keys are set, and `MODEL_NAME` overrides the preset's default model. Only the `single` and `staged` architectures call a model; `rules` needs no key.

| Key in `.env` | Provider | Default model |
|---|---|---|
| `ANTHROPIC_API_KEY` | Anthropic | `claude-opus-5-5` |
| `OPENAI_API_KEY` | OpenAI | `gpt-5-mini` |
| `GEMINI_API_KEY` | Google AI Studio (free tier) | `gemini-3.1-flash-lite` |
| `OPENROUTER_API_KEY` | OpenRouter (free models) | `nvidia/nemotron-3-super-120b-a12b:free` |
| `OPENAI_COMPAT_API_KEY` + `OPENAI_COMPAT_BASE_URL` + `MODEL_NAME` | any OpenAI-compatible endpoint | – |

The result is policy-compliant on any of them: thresholds, budget, expiry, required fields and injection are decided in code, and the guardrail corrects whatever the model gets wrong. A weaker model shows more guardrail corrections in the UI and the evaluation; a stronger one fewer. If an endpoint rejects forced tool choice or strict JSON output, the adapter drops that feature and retries, so it degrades instead of failing. Free tiers are rate-limited; the comparison script saves every decision and supports `--resume`.

## Product workflow

```
Request -> Understand need -> Gather evidence (5 tools) -> Deterministic policy checks
        -> Model drafts recommendation -> Code guardrail -> Human review (UI actions are logged, never executed)
```

The UI has three panels: **Request details**, **Evidence** (every finding names the tool it came from, with the full tool trace and the model's pre-guardrail draft), and **Recommendation + action** (approvals required, risk flags, missing information, next step, telemetry, reviewer buttons). The reviewer can also record an **override** with their own recommendation and a required reason; the log keeps both the copilot's and the reviewer's call.

The sidebar takes either a **sample request** from the dataset or a **custom request** typed in on the spot, so new or adversarial cases can be tested live without editing data files. Blank fields are treated as missing information, and every field is handled as untrusted data.

![Overview: budget breach on a new vendor with customer PII](docs/screenshot_overview.png)

Evidence trace and guardrail view, and the incomplete request with a prompt-injection attempt:

| ![Evidence and recommendation](docs/screenshot_evidence.png) | ![Clarification with injection flagged](docs/screenshot_clarification.png) |
|---|---|

Output contract (`src/contracts.py`): recommendation · evidence · required approvals · missing information · risk flags · next step · human review flag · telemetry.

## Architecture, tools and agents

Diagrams, assumptions and reliability controls: [docs/architecture.md](docs/architecture.md).

| | A: single agent | B: staged (2 agents) | rules (baseline, not a candidate) |
|---|---|---|---|
| Model calls | one agent, tool loop | Analyst (tools) → Reviewer (no tools) | none |
| Measured LLM calls | 3 (tool turn, answer, JSON formatting) | 4 | 0 |
| Deterministic layer | same `run_policy_checks` + guardrail | same | same |

**Tools (all deterministic):** `get_requester_and_budget`, `search_software_catalog`, `get_vendor_status` (registry + risk API, 365-day currency, conflict detection), `run_policy_checks` (the policy engine), `lookup_policy`.

**Code guardrail (both architectures):** approvals and flags can never be weaker than policy; code-owned facts (budget, availability, expiry, conflict, missing information) are set by code; flags outside the taxonomy are dropped; evidence is dropped unless it names a tool the agent actually called **and** every number or date it quotes appears in a tool result, the request or the policy text; deterministic findings fill any evidence gap; `approve` is blocked when any blocking flag exists; over-budget forces the Finance exception route; human review is always required. Every correction is recorded, and the raw model draft is kept so evaluation can score the model on its own.

**Reliability controls:** request fields normalised before any rule runs (numeric strings, blank values, string-typed integration lists); an unrecognised `data_access_level` is treated as unclassified (Security review plus a clarification item) rather than silently internal; vendor API 503/404/unreachable → `vendor_risk_unavailable` and manual review (the adapter starts the local mock API if it is down; set `AUTO_START_MOCK_API=false` to demo an outage); model failure → rules-only decision with `llm_unavailable`; request text and vendor notes scanned for injection; a completeness gate rejects any model answer produced before the four core tools were consulted; junk tool arguments from weaker models are ignored and logged.

## Evaluation

The brief's six edge cases are all in the test set, each with the deterministic behaviour the system must show:

| Edge case (brief) | Case ids | What the system does |
|---|---|---|
| Incomplete / ambiguous request | PUB-05, SYN-05 | `missing_information` flag, clarification items from policy §1, `request_clarification` |
| Existing tool already solves the need | PUB-02, EXT-03, SYN-02 | `existing_tool_overlap`, exact duplicate routed to `evaluate_existing_tool_first` |
| Conflicting or expired vendor information | EXT-02, SYN-01 | `conflicting_vendor_evidence` / `vendor_review_expired`, Security added, manual review |
| Security-sensitive request or approval threshold | PUB-03, PUB-04, EXT-01, SYN-03, SYN-04 | Security / Privacy / Legal approvals, CFO above $25k, Finance exception when over budget |
| Prompt injection inside business data | PUB-05, SYN-02 | `prompt_injection_detected`, instructions ignored, routed to manual review |
| Tool / API unavailable | PUB-06 | `vendor_risk_unavailable`, never a favourable default, manual review |

Same 15 cases on every architecture: the 6 public cases, the 4 remaining starter requests (conflict/expired vendor, exact duplicate, AI tool on customer PII, training pack) and 5 synthetic hidden-style cases (unknown vendor, injection in product name, >$25k over budget, employee PII, missing justification). Expectations in `evals/extended_cases.json`.

The brief asks for five things to be evaluated; each maps to a row in the report, plus two rows that score the model on its own before the guardrail:

| Brief criterion | Report row |
|---|---|
| Correct recommendation / next action | Final recommendation correct (the case's accepted codes) |
| Evidence grounded in tool results | Model evidence grounded: source tool called, and quoted values present in tool results |
| Policy and deterministic rules followed | Cases passing minimum checks (starter expectations), policy corrections the guardrail had to make |
| Escalation / human review correct | Escalation / human review correct: human review flagged and every expected approver routed |
| Latency, LLM and tool call count | Avg latency, LLM calls, tool calls, tokens |

The model's own recommendation before the guardrail is scored separately, so the table shows what the agent got right versus what code had to fix.

Results (15 cases × 3 runs, model `gemini-3.1-flash-lite`; full table and per-case detail in [evals/results/comparison_summary.md](evals/results/comparison_summary.md), every decision in `evals/results/decisions/`):

| Metric | single | staged | rules |
|---|---:|---:|---:|
| Cases passing minimum checks | 45/45 | 45/45 | 45/45 |
| Final recommendation correct | 44/45 | 44/45 | 45/45 |
| Escalation / human review correct | 45/45 | 45/45 | 45/45 |
| Model's own recommendation correct (pre-guardrail) | 44/45 | 43/45 | – |
| Model evidence grounded: source tool / quoted values | 95% / 99% | 100% / 99% | – |
| Avg latency | 14.9 s | 20.2 s | 52 ms |
| Avg LLM calls / tool calls | 3.0 / 4.0 | 4.0 / 4.0 | 0 / 4.0 |
| Avg input / output tokens | 9.8k / 0.9k | 13.9k / 1.4k | 0 |

The one remaining miss is run-to-run variance: each agent under-routed the employee-PII request once in three runs, and the guardrail added Security and Privacy both times, so the output stayed policy-compliant. An earlier version of the overlap rule treated any product-name match as a duplicate, which sent a training pack for an approved tool to "evaluate existing tool first" on every architecture; the rule now separates a same-category match (possible duplicate) from an add-on or service in another category, and the rules baseline is correct on all 15 cases.

A first single-agent run on a weaker free model (`nvidia/nemotron-3-super-120b-a12b:free`, archived in `evals/results/archive_nemotron_single/`) scored 7/15 before the guardrail and 13/15 after it, with 2.8 corrections per case. Model quality mattered more than architecture; the deterministic layer is what keeps weak models safe.

## Ship decision

**Single agent.** Identical minimum-check and recommendation scores to the staged variant over three runs, with one fewer model call, 27% lower latency and 31% fewer tokens. Full reasoning in [docs/decision_memo.md](docs/decision_memo.md).

## Scaffold fixes

- Mock API decoded the vendor name twice (FastAPI already decodes path parameters).
- Public eval runner did not start the mock API, so a cold run flagged every vendor unavailable; it now starts it.
- Streamlit scaffold used the deprecated `use_container_width`.
- `.env` now overrides shell variables so a stale OS key cannot shadow the project key.

## Assumptions

Full list in [docs/architecture.md](docs/architecture.md#assumptions). The ones that shape results most:

- Dates compare against the policy reference date (2026-09-30), read from the policy file, never the machine clock. A vendor security assessment is current for 365 days from the risk service's `last_review_date`.
- "New vendor" means the registry status is not Approved, or the vendor is missing from the registry.
- `data_access_level` is free text, mapped to policy classes by keyword. Blank or "unknown" is missing information; text matching no keyword is treated as sensitive until a human confirms it.
- An empty `requested_integrations` list means "none needed"; a missing field is a gap.
- Legal review also triggers when registry legal terms are not Approved/Standard, even below $10k.
- Prompt injection does not reject a request; it routes it to manual review and its instructions are ignored.
- The copilot never approves, purchases or changes a budget. Reviewer buttons log a decision for the approvers.

## Known limitations

- Free-tier models: 8–30 s per case; weaker ones emit junk flags, duplicate tool calls or skip tools. The guardrail, completeness gate and grounding check absorb these, and the evaluation reports them rather than hiding them.
- Value grounding checks that quoted numbers exist in the data the model saw, not that the reasoning linking them is right. Values the model derives itself (for example a computed expiry date) are dropped as unverifiable, which is conservative.
- Data classification is keyword-based; unusual phrasing falls back to "unclassified" and asks for confirmation rather than guessing, so some clean requests may get an extra question.
- Reviewer actions are logged to a local file; there is no identity, workflow engine or notification.
- Three evaluation runs per architecture on one free model. Variance appeared on one case for each agent; a stronger model and more repeats are needed before production claims.
- The `evaluate existing tool` vs `approve` judgment for add-ons is accepted both ways for the seat add-on case (policy §3 supports both), see the note in `evals/extended_cases.json`.
