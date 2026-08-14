# 09 — Deployment lifecycle

## Hai deployment target

- **Lab:** Metrics Simulator, Prometheus, Alertmanager, Grafana, OTel Collector và
  Tempo bằng Docker Compose; toàn bộ dữ liệu/trace là synthetic.
- **V-ID UAT/production:** instrumentation tại workload thật, service discovery,
  retention/storage/HA/security theo platform convention. Lab Compose không phải
  production manifest.

## Vòng đời

```text
v-id-intern-docs + owner confirmation
→ metric/trace contract
→ implementation + tests
→ review/CI
→ UAT with real topology
→ evidence and threshold approval
→ promote or rollback
```

Trước UAT phải xác nhận:

- Workload và route thực tế; dev/prod hiện có gateway drift.
- Trạng thái migration `account` → `identity-provider-web` và Hydra-as-issuer.
- Service/metric owner, SLO và alert notification route.
- Provider delivery receipt semantics và data/privacy policy.
- OTel sampling, collector capacity, Tempo retention và access control.

## Artifacts

Dashboard JSON, Prometheus/Alertmanager rules, datasource/Collector/Tempo config,
tests và docs đều nằm trong Git. Secret được inject ngoài repository. Rollback
bằng revert/deploy artifact ổn định trước đó; hotfix phải đồng bộ về Git.

## Production instrumentation handoff

Propagate W3C `traceparent` qua Kong, HTTP/gRPC và Kafka headers; instrument caller
và server boundary, Redis/DB và provider client. Delivery callback được correlate
bằng identifier đã privacy-review. Không copy phone/OTP/token vào telemetry.
