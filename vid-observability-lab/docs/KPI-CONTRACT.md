# V-ID KPI Contract

Status: **proposed for UAT**. Service owner and SRE must approve every row before
production. `TBD` is a release blocker, not an optional field.

| KPI | Owner | Good events | Eligible events | Exclusions | SLO/window |
|---|---|---|---|---|---|
| Authentication success | TBD: Auth owner | `result="success"` | `reason=~"none|system_error"` | invalid credential, locked, expired | 99.9% / rolling 30d |
| Authentication latency | TBD: Auth owner | eligible histogram bucket `le="0.5"` | eligible histogram count | business/user rejection | 95% / rolling 30d |
| OTP delivery | TBD: OTP owner | `result="delivered"` | terminal result with `none`, `provider_error`, `timeout` | pending, invalid destination, client rate limit | 95% / 24h and 30d |
| OTP verification | TBD: OTP owner | `result="success"` | all terminal verification attempts | none for product baseline | baseline; no SLO alert |
| Token issuance | TBD: Token owner | `result="issued"` | `none`, signing, storage and system outcomes | `invalid_grant` | 99.9% / rolling 30d |
| Platform availability | TBD: Platform owner | critical non-5xx | all critical terminal requests | non-critical endpoints | 99.9% / rolling 30d |

## Decision log required before production

The approval pull request must record:

1. Business owner and technical owner for each KPI.
2. Whether client rate limiting belongs in each denominator.
3. Whether OTP verification is a product conversion KPI or a service SLI.
4. The authoritative critical-endpoint allowlist.
5. Minimum traffic thresholds for alerts.
6. Approved SLO targets, rolling windows and timezone/reporting policy.
7. Production dashboard and runbook base URLs.

## Label contract

`environment` and `cluster` are target labels injected by service discovery or
scrape configuration. Domain labels come from instrumentation and have bounded
values. Do not add user ID, phone number, email, token, OTP, request ID, session
ID, raw URL or free-form exception text.

Before adding a dimension, estimate the resulting series count, including every
histogram bucket. Provider, channel, grant type, service, endpoint and client type
are permitted only while they stay within the agreed cardinality budget.

## Counter and retry semantics

- Counters may reset only when a process restarts.
- OTP delivery metrics count provider attempts, not unique user journeys.
- A retry is another attempt. Journey-level KPIs require a separate bounded
  journey outcome metric; never add journey ID as a label.
- Recording rules aggregate instance/pod labels but preserve environment and
  cluster.
- A ratio is not actionable when eligible traffic is absent; data-health and
  traffic checks must be evaluated first.
