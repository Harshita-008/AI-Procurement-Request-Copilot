# Architecture comparison

15 cases. Runs per architecture: single=1, rules=1.
Models: single=nvidia/nemotron-3-super-120b-a12b:free, rules=none

| Metric | single | rules |
|---|---:|---:|
| Cases passing minimum checks | 15/15 | 15/15 |
| Final recommendation correct | 13/15 | 13/15 |
| Model's own recommendation correct (pre-guardrail) | 7/15 | - |
| Model evidence grounded in tool results | 1.00 | - |
| Policy corrections needed per case | 2.80 | 0.00 |
| Avg latency (ms) | 19430 | 28 |
| Avg LLM calls | 2.87 | 0.00 |
| Avg tool calls | 6.20 | 4.00 |
| Avg input tokens | 9490 | 0 |
| Avg output tokens | 1650 | 0 |
| Avg cost per case (USD) | 0.0000 | - |

## Per case (final recommendation correct / minimum checks)

| Case | Title | single | rules |
|---|---|---|---|
| PUB-01 | Low-value approved vendor add-on | 1/1 / 1/1 | 0/1 / 1/1 |
| PUB-02 | Existing alternatives + new vendor | 1/1 / 1/1 | 1/1 / 1/1 |
| PUB-03 | Sensitive source-code access | 1/1 / 1/1 | 1/1 / 1/1 |
| PUB-04 | Budget shortfall + new sensitive vendor | 1/1 / 1/1 | 1/1 / 1/1 |
| PUB-05 | Incomplete request + prompt injection | 1/1 / 1/1 | 1/1 / 1/1 |
| PUB-06 | Vendor-risk API unavailable | 1/1 / 1/1 | 1/1 / 1/1 |
| EXT-01 | Approved AI tool pointed at customer PII | 0/1 / 1/1 | 1/1 / 1/1 |
| EXT-02 | Registry/API conflict + expired review + production access | 1/1 / 1/1 | 1/1 / 1/1 |
| EXT-03 | Exact duplicate of a company-wide tool | 0/1 / 1/1 | 1/1 / 1/1 |
| EXT-04 | Low-value training pack, no data access | 1/1 / 1/1 | 0/1 / 1/1 |
| SYN-01 | Vendor unknown to registry and risk service | 1/1 / 1/1 | 1/1 / 1/1 |
| SYN-02 | Injection hidden in product name, otherwise clean | 1/1 / 1/1 | 1/1 / 1/1 |
| SYN-03 | Above $25k with budget shortfall, approved vendor | 1/1 / 1/1 | 1/1 / 1/1 |
| SYN-04 | Employee PII on an approved vendor | 1/1 / 1/1 | 1/1 / 1/1 |
| SYN-05 | No business justification given | 1/1 / 1/1 | 1/1 / 1/1 |
