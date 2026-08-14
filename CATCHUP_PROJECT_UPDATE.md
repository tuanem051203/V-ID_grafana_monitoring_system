# Cập nhật V-ID Observability Lab

## Kết quả hiện tại

Lab đã có Metrics Simulator, Prometheus recording/alert rules, Alertmanager,
Grafana dashboards, OpenTelemetry Collector và Tempo. Toàn bộ dữ liệu là
synthetic; mục tiêu là review contract và demo triage trước khi kết nối UAT.

## Mapping đã đồng bộ với V-ID docs

- Authentication/OTP thuộc `identity-provider`; web OIDC đi qua Hydra.
- `oauth2-token` là component transition, không phải token issuer cuối cùng; target
  ADR-0007 là Hydra-as-issuer.
- Authorization dùng `authz`, với `organization` là organization source of truth.
- International OTP route qua Notification Center hoặc GSM/WhatsApp theo policy;
  provider acceptance và carrier delivery receipt là hai boundary khác nhau.
- Kong là gateway trên request path; Redis/Postgres/Kafka là dependencies.
- `account` đang decommission; `identity-provider-web`/Account Center routing còn
  khác giữa dev và prod.

Tên `auth-service`, `otp-service`, `token-service` còn xuất hiện trong simulator
chỉ là synthetic aliases, không phải inventory V-ID production.

## Demo observability

Prometheus/Grafana xác định flow, country/provider và stage đang suy giảm. 10% OTP
journey được phát thành synthetic trace qua OTel Collector tới Tempo; exemplar cho
phép mở waterfall từ Grafana.

OTP journey demo:

```text
edge → Kong → IdP → Redis → route selection → queue → GSM → delivery receipt
```

Scenario có thể làm chậm riêng `kong_to_idp`, `redis_challenge`, `queue_wait`,
`gsm_submit` hoặc `carrier_delivery` để minh họa bottleneck.

## Việc cần phối hợp trước UAT

1. Xác nhận workload, gateway route và owner thực tế.
2. Chốt current/transition/target flow, đặc biệt Hydra-as-issuer.
3. Kiểm kê metrics/OpenTelemetry hiện có trong Go services và Kong.
4. Chốt SLI/SLO, traffic floor, exclusions và notification route.
5. Xác nhận GSM/provider delivery-report contract và privacy policy.
6. Thay synthetic aliases/topology bằng service discovery và telemetry thật.
7. Kiểm thử UAT, lưu dashboard/trace/alert evidence và phương án rollback.
