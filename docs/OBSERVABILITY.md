# V-ID Observability Handbook

Tài liệu này gộp thiết kế observability của repository. Nguồn domain chuẩn là
[`v-id-intern-docs`](v-id-intern-docs/README.md); contract executable nằm trong
[`vid-observability-lab`](../vid-observability-lab/README.md).

## 1. Scope và kiến trúc

V-ID là identity platform, không phải một `auth-service` đơn lẻ. Lab ưu tiên:

1. Native/transition SMS OTP challenge tại `identity-provider`.
2. Browser Authorization Code + PKCE qua Hydra và IdP login/consent.
3. International OTP qua routing, Notification Center/GSM và delivery receipt.
4. Token lifecycle trong giai đoạn dual issuer.
5. Organization-scoped RBAC qua `authz` và `organization`.

```text
V-ID services/dependencies
  ├─ metrics ──> Prometheus ──> rules ──> Alertmanager
  ├─ spans ────> OTel Collector ─────────> Tempo
  └─ logs ─────> production log backend (chưa có trong lab)

Prometheus + Tempo ──> Grafana / metrics-to-trace drill-down
```

`trace_id`, request ID và dữ liệu định danh không được dùng làm Prometheus label.

## 2. KPI, SLI và SLO

| Signal | Production boundary cần xác nhận | Lab target |
|---|---|---|
| Authentication success | IdP terminal auth hoặc Hydra web completion | 99.9% / 30d |
| Authentication latency | cùng boundary với flow đã chọn | 95% dưới 500 ms / 30d |
| OTP provider submission | Notification Center/GSM client result | baseline trước |
| OTP delivery | authoritative delivery receipt | 95% / 24h và 30d |
| OTP verification | IdP terminal verify result | baseline, chưa alert SLO |
| Token issuance | event theo Hydra/IdP issuer thực tế | 99.9% / 30d |
| Platform availability | valid critical Kong/service request | 99.9% / 30d |
| AuthZ decision | valid `authz` enforcement request | đề xuất, chưa có SLO lab |

Target chỉ dùng kiểm thử. Invalid credential, wrong/expired OTP và policy denial
là business outcome trừ khi owner phê duyệt đưa vào availability. Provider
acceptance không đồng nghĩa thiết bị đã nhận SMS.

```text
allowed_bad_ratio = 1 - SLO
burn_rate = observed_bad_ratio / allowed_bad_ratio
```

Page bằng multi-window burn rate khi đủ traffic; no-data khác 0% lỗi và khác 100%
thành công. Xem [KPI contract](../vid-observability-lab/docs/KPI-CONTRACT.md).

## 3. Metric contract

| Nhóm synthetic | Mapping production cần xác nhận |
|---|---|
| `auth_*` | IdP native/step-up hoặc Hydra web completion |
| `otp_send_*`, `otp_delivery_*`, `otp_verify_*` | IdP route, Notification Center, GSM/WhatsApp, callback |
| `otp_journey_*`, `otp_stage_*` | Kong → IdP → Redis → routing → queue → provider |
| `token_*` | Hydra issuer, IdP transition issuer, `oauth2-token` front |
| `http_request_*` | Kong và từng deployment/operation thật |
| `authorization_decisions_*` | `authz` enforce; denial không mặc định error |
| dependency metrics | Redis/Postgres/Kafka/provider instrumentation |

OTP stages: `edge_to_kong`, `kong_to_idp`, `redis_challenge`, `route_selection`,
`queue_wait`, `gsm_submit`, `carrier_delivery`. Stage cuối là asynchronous receipt,
không phải HTTP hop đồng bộ.

Allowed bounded labels: `environment`, `cluster`, `service`, `operation`, `result`,
`reason`, `status_class`, `client_type`, `realm`, `issuer`, `grant_type`, `channel`,
`provider`, `destination_country`, `stage`.

Forbidden: phone/email, user/session/challenge/request/trace ID, OTP, token, cookie,
authorization code, parameterized raw URL, free-form error và stack trace. Counter
dùng `rate`/`increase`; histogram dùng seconds; numerator phải là tập con của
denominator và cùng boundary.

## 4. Prometheus, Grafana và tracing

Production dùng `ServiceMonitor`/`PodMonitor` theo workload thật thay cho static
hostname. Prometheus gắn `environment`/`cluster`, bật exemplar và aggregate
histogram theo `le` trước `histogram_quantile`.

| Dashboard | Insight chính |
|---|---|
| Overview | AuthN, OTP, token và platform symptoms |
| Authentication | đăng nhập và xác thực |
| MFA & OTP | send, delivery và verification |
| OTP Journey | stage latency/error và Tempo exemplar |
| Token Lifecycle | issue/refresh/revoke và issuer boundary |
| Authorization | decision, denial và system error |
| Platform & Dependencies | HTTP, resource và dependency health |
| SLO & Incidents | error budget, burn rate và active alert |
| Cross-region Requests | synthetic RED test, không phải V-ID topology |

Dashboard cần stable UID, đúng unit, mô tả boundary, phân biệt no-data/zero và
không chứa credential/URL cá nhân.

## 5. Alerting và triage

Page theo user impact/burn rate, không chỉ vì CPU/pod. Alert cần owner,
environment, service, dashboard và runbook.

1. Xác nhận environment, flow, client/realm và issuer.
2. Từ Overview mở dashboard chi tiết.
3. Tìm service/stage đầu tiên suy giảm bằng bounded labels.
4. Mở Tempo exemplar; kiểm tra deployment/config change.
5. Phân biệt IdP/Kong, Redis, queue, provider submit và carrier receipt.
6. Mitigate theo quyền hạn; xác nhận traffic/SLI phục hồi và ghi timeline.

Chi tiết: [Runbook](../vid-observability-lab/docs/RUNBOOK.md).

## 6. Source of truth và lifecycle

```text
docs/v-id-intern-docs/                  V-ID domain snapshot
vid-observability-lab/services/         synthetic simulator
vid-observability-lab/observability/    rules, dashboards, Alertmanager
vid-observability-lab/deployments/      environment config/templates
vid-observability-lab/tests/            dashboard/rule contracts
vid-observability-lab/docs/             operational contract/runbook
```

Không sửa `generated/<environment>`; tạo lại bằng `render-config.py`. Lab Compose
không phải production manifest.

```text
v-id-intern-docs + owner confirmation
→ telemetry contract → implementation + tests → review
→ UAT topology thật → evidence/threshold approval → promote hoặc rollback
```

Trước UAT phải xác nhận workload/route, Hydra migration, owner, notification,
receipt semantics, privacy, OTel capacity, retention, SSO/RBAC, TLS, secret, HA
và rollback. Propagate W3C `traceparent`; correlation ID chỉ dùng sau privacy review.

## 7. Review checklist

- Mapping tới component/flow nào trong `v-id-intern-docs`?
- Đây là current, transition hay ADR target?
- Synthetic assumption đã được đánh dấu chưa?
- Metric có PII/high cardinality hoặc sai numerator/denominator không?
- Issuer và provider-acceptance/delivery boundary có nhất quán không?
- Simulator, rules, dashboard, config, tests và docs đã đồng bộ chưa?
- Có owner, UAT evidence, runbook, notification route và rollback chưa?
