# 04 — Prometheus cho V-ID

## Target discovery

Production không dùng static hostname minh họa. Dùng `ServiceMonitor`/`PodMonitor`
theo convention của cluster và scrape metrics port riêng của từng deployment:

- `identity-provider`, `identity-provider-web`, admin/query deployment nếu có.
- `oauth2-server` (Hydra) và `oauth2-token`.
- `authz`, `organization` và các service critical khác.
- Kong, Redis/Postgres/Kafka exporter và provider integration metrics.

Dev/prod routing đang drift theo
[`gateway-routing.md`](v-id-intern-docs/docs/architecture/gateway-routing.md); service
discovery phải dựa trên workload thực tế, không suy ra từ public hostname.

## External labels

Prometheus gắn `environment` và `cluster`. Service tự xuất bounded dimensions như
operation/result/provider; không để client tự cung cấp label tùy ý.

## Recording rules

Lab hiện có:

- KPI rules cho authentication, OTP, token và availability.
- Cross-region synthetic RED rules.
- OTP journey rules cho end-to-end, stage latency/error và delivery receipt.

Quy ước: `vid:<signal>:<aggregation/window>`. Ratio phải dùng cùng eligible set và
`clamp_min` để tránh chia zero. Histogram aggregate theo `le` trước khi gọi
`histogram_quantile`.

## Metrics-to-traces

Prometheus bật exemplar storage. Histogram OTP journey có exemplar `trace_id` để
Grafana mở Tempo. Không thêm `trace_id` thành time-series label.

## Validation

```bash
promtool check config generated/local/prometheus/prometheus.yml
promtool check rules generated/local/prometheus/rules/*.yml
promtool test rules tests/prometheus/*.test.yml
```

Test tối thiểu gồm normal, degradation, low/no traffic, counter reset, pending →
firing → resolved và label preservation. Retention phải đủ cho SLO window.
