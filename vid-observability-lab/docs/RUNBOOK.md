# V-ID Monitoring Runbook

Replace `REPLACE-WITH-DOCS-HOST` in alert annotations with the published runbook
base URL before production.

## First response for every alert

1. Confirm `environment`, `cluster`, `service`, alert start time and user impact.
2. Open **V-ID SSO — SLO & Sự cố** and check target health, eligible traffic,
   active alerts and rule evaluation failures.
3. If telemetry is healthy, open **V-ID SSO — Tổng quan** and identify the
   affected reason/provider/endpoint.
4. Check the most recent deployment and configuration changes.
5. Apply only an approved mitigation; record timestamps and evidence.
6. Confirm recovery on both the short and confirmation windows before resolving.

## Metrics target down

- Check `/health` and `/metrics` directly from the Prometheus network.
- Check service discovery labels, DNS, port, network policy and TLS/auth config.
- Inspect exporter logs and Prometheus target error.
- Do not interpret missing KPI series as a healthy zero-error state.

## Rule evaluation failure

- Open Prometheus `/rules` and inspect the exact failing group/expression.
- Check metric names, label changes, duplicate series and query resource limits.
- Run `promtool check rules` and `promtool test rules` against the deployed commit.
- Roll back the rule-only change if it is the confirmed cause.

## No eligible traffic

- Compare target `up`, raw request counters and expected business traffic.
- Confirm deployment has not changed result/reason taxonomy.
- Confirm filters have not excluded all events.
- For genuinely quiet environments, adjust routing or minimum-traffic policy
  through review; do not simply remove no-data detection.

## Authentication success or token issuance burn

- Break failures down by bounded `reason`, client/grant type and endpoint.
- Distinguish business rejection from signing, storage, dependency and system
  errors.
- Check dependency health, rollout status, saturation and error logs.
- Consider rollback or traffic shift according to the service deployment runbook.

## Authentication latency burn

- Compare p50/p95/p99 and under-500ms ratio.
- Check in-progress gauges, request rate, CPU/memory and downstream latency.
- Identify whether degradation is global or isolated by client/cluster.
- Mitigate saturation, dependency latency or a regression using approved actions.

## OTP delivery/provider incident

- Check provider state, queue depth, failure reasons and channels.
- Confirm provider status outside V-ID and whether fallback routing is available.
- Apply provider failover/rate controls only through the OTP operations procedure.
- Track backlog recovery after provider service returns.

## Platform availability burn

- Break 5xx down by service and critical endpoint.
- Identify common dependency or rollout correlation across services.
- Verify that the critical-endpoint allowlist is still correct.
- Coordinate incident ownership when multiple identity services are affected.

## Closure

Record impact, timeline, root cause, mitigation, dashboard evidence and follow-up
actions. A production alert is not complete until its owner, notification route,
dashboard link and published runbook link are verified.
