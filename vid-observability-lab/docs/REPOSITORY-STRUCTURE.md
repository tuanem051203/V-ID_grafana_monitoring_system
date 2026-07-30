# Repository Structure Decision

## Scope

`vid-observability-lab` is a local/UAT observability workspace, not the
production deployment repository. Its boundaries follow deployable component,
platform configuration, deployment profile, test and operational-document
ownership.

| Path | Ownership | Change validation |
|---|---|---|
| `services/metrics-simulator` | Simulator application team | Python type/lint/test and image build |
| `observability/prometheus` | SRE/observability | `promtool check/test rules` |
| `observability/grafana` | SRE + service owners | JSON/schema and dashboard review |
| `observability/alertmanager` | SRE/on-call governance | `amtool check-config`, routing review |
| `deployments/local` | Developer experience | `docker compose config`, smoke test |
| `tests/prometheus` | SRE + KPI owners | Rule behavior tests |
| `docs` | KPI owners + SRE | Approval and runbook review |
| `scripts` | Platform engineering | Reproducible validation entry points |

## Why the old layout was changed

The old flat project mixed Python source, Docker Compose, Prometheus, Grafana and
Alertmanager at the same level. That made build context, code ownership,
deployment scope and CI change detection ambiguous. The new layout makes the
metrics simulator independently packageable and explicitly marks Compose as a
local deployment profile.

## Production repository expectations

Before adopting this workspace for production, the owning organization must
choose the platform-specific structure rather than copying local Compose:

```text
deployments/
├── local/
├── uat/          # Helm values or Kustomize overlay
└── production/   # Reviewed promotion artifact, no plaintext secrets
```

A production repository should additionally provide:

- `CODEOWNERS` or the equivalent approval policy.
- CI jobs scoped by path and protected-environment promotion.
- Helm/Kustomize or the organization's standard deployment abstraction.
- External secret references, SSO/RBAC/TLS and network policies.
- HA, retention, storage, backup and disaster-recovery configuration.
- Dashboard/rule release versioning and rollback evidence.
- Environment-specific service discovery instead of static targets.

These additions depend on the company's Git platform, Kubernetes/deployment
standard, secret manager, identity provider and on-call system. They are
intentionally documented as integration decisions instead of being guessed in
the local lab.
