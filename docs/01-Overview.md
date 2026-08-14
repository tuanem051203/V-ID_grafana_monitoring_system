# 01 — Tổng quan observability V-ID

## Nguồn kiến trúc

Tài liệu này được dẫn xuất từ snapshot nội bộ tại
[`v-id-intern-docs`](v-id-intern-docs/README.md), đặc biệt là
[`architecture.md`](v-id-intern-docs/docs/architecture/architecture.md),
[`components.md`](v-id-intern-docs/docs/architecture/components.md) và
[`gateway-routing.md`](v-id-intern-docs/docs/architecture/gateway-routing.md).
Khi có khác biệt, tài liệu nội bộ là nguồn chuẩn và cần xác nhận lại với living
document trước khi triển khai.

## Phạm vi V-ID cần quan sát

V-ID là identity platform, không phải một `auth-service` đơn lẻ. Request path hiện
có các thành phần chính:

- `identity-provider`: identity broker, OTP, profile, session, login/consent UI và
  hiện vẫn còn các seam phát hành token trong giai đoạn chuyển đổi.
- Ory Hydra (`oauth2-server`): OAuth2/OIDC surface và issuer của web flow; theo
  ADR-0007 sẽ trở thành sole issuer.
- `oauth2-token`: token front/router đang chuyển dần sang Hydra front.
- `authz`: RBAC engine; `organization` là source of truth cho organization.
- Kong: API gateway trên request path.
- Redis/Postgres/Kafka: state, persistence và event transport.
- Notification Center và GSM SMS gateway: dependency gửi OTP; +84 giữ route
  Notification Center, quốc gia allowlist có thể đi GSM/WhatsApp.

`account` đang decommission; `identity-provider-web` và Account Center có trạng
thái/routing khác nhau giữa dev và prod. Dashboard phải filter theo deployment
thực tế, không gộp chúng thành một service tưởng tượng.

## Luồng telemetry

```text
V-ID services/dependencies
  ├─ Prometheus metrics ──> Prometheus ──> rules/alerts ──> Alertmanager
  ├─ OpenTelemetry spans ─> OTel Collector ──────────────> Tempo
  └─ structured logs ─────> log backend (production integration)

Prometheus + Tempo ──> Grafana dashboards / Metrics-to-Trace drill-down
```

Metrics trả lời “nhóm request nào đang lỗi/chậm”; trace trả lời “một request đã
mất thời gian ở boundary nào”. `trace_id`, request ID và thông tin định danh không
được dùng làm Prometheus label.

## User journeys ưu tiên

1. Native/transition SMS OTP challenge: `/v1/auth/challenge` → verify → login.
2. Browser OIDC Auth Code + PKCE: client → Hydra → IdP login/consent → Hydra.
3. International OTP: IdP route selection → Notification Center hoặc GSM/WhatsApp.
4. Token exchange/refresh/revoke/introspection trong giai đoạn dual issuer và
   target Hydra-as-issuer.
5. AuthZ enforcement: downstream caller → `authz`, với organization-scoped RBAC.

Luồng native V-App trong tài liệu kiến trúc đã được đánh dấu deprecated theo
ADR-0007; simulator vẫn giữ metric tương ứng để biểu diễn giai đoạn chuyển đổi,
không khẳng định đó là target architecture.

## Trạng thái lab

Lab dùng dữ liệu synthetic để phát triển contract, dashboard và alert. Topology
cross-region generic chỉ là test scenario. Quốc gia của số điện thoại không chứng
minh request chạy qua datacenter tại quốc gia đó. Với OTP, boundary đúng để demo
là Kong → IdP → Redis/routing → queue → GSM/provider → delivery receipt.
