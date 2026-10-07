# Architecture comparison

15 cases. Runs per architecture: single=3, staged=3, rules=3.
Models: single=gemini-3.1-flash-lite, staged=gemini-3.1-flash-lite, rules=none

| Metric | single | staged | rules |
|---|---:|---:|---:|
| Cases passing minimum checks | 45/45 | 45/45 | 45/45 |
| Final recommendation correct | 41/45 | 41/45 | 42/45 |
| Model's own recommendation correct (pre-guardrail) | 41/45 | 40/45 | - |
| Model evidence grounded in tool results (source) | 0.91 | 1.00 | - |
| Model evidence values verified against tool results | 0.99 | 0.99 | - |
| Policy corrections needed per case | 0.00 | 0.00 | 0.00 |
| Avg latency (ms) | 12780 | 16950 | 31 |
| Avg LLM calls | 3.00 | 4.00 | 0.00 |
| Avg tool calls | 4.00 | 4.00 | 4.00 |
| Avg input tokens | 9765 | 13923 | 0 |
| Avg output tokens | 864 | 1427 | 0 |
| Avg cost per case (USD) | - | - | - |

## Per case (final recommendation correct / minimum checks)

| Case | Title | single | staged | rules |
|---|---|---|---|---|
| PUB-01 | Low-value approved vendor add-on | 3/3 / 3/3 | 3/3 / 3/3 | 3/3 / 3/3 |
| PUB-02 | Existing alternatives + new vendor | 3/3 / 3/3 | 3/3 / 3/3 | 3/3 / 3/3 |
| PUB-03 | Sensitive source-code access | 3/3 / 3/3 | 3/3 / 3/3 | 3/3 / 3/3 |
| PUB-04 | Budget shortfall + new sensitive vendor | 3/3 / 3/3 | 3/3 / 3/3 | 3/3 / 3/3 |
| PUB-05 | Incomplete request + prompt injection | 3/3 / 3/3 | 3/3 / 3/3 | 3/3 / 3/3 |
| PUB-06 | Vendor-risk API unavailable | 3/3 / 3/3 | 3/3 / 3/3 | 3/3 / 3/3 |
| EXT-01 | Approved AI tool pointed at customer PII | 3/3 / 3/3 | 3/3 / 3/3 | 3/3 / 3/3 |
| EXT-02 | Registry/API conflict + expired review + production access | 3/3 / 3/3 | 3/3 / 3/3 | 3/3 / 3/3 |
| EXT-03 | Exact duplicate of a company-wide tool | 3/3 / 3/3 | 3/3 / 3/3 | 3/3 / 3/3 |
| EXT-04 | Low-value training pack, no data access | 0/3 / 3/3 | 0/3 / 3/3 | 0/3 / 3/3 |
| SYN-01 | Vendor unknown to registry and risk service | 3/3 / 3/3 | 3/3 / 3/3 | 3/3 / 3/3 |
| SYN-02 | Injection hidden in product name, otherwise clean | 3/3 / 3/3 | 3/3 / 3/3 | 3/3 / 3/3 |
| SYN-03 | Above $25k with budget shortfall, approved vendor | 3/3 / 3/3 | 3/3 / 3/3 | 3/3 / 3/3 |
| SYN-04 | Employee PII on an approved vendor | 2/3 / 3/3 | 2/3 / 3/3 | 3/3 / 3/3 |
| SYN-05 | No business justification given | 3/3 / 3/3 | 3/3 / 3/3 | 3/3 / 3/3 |
