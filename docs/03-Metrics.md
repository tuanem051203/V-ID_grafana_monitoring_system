# 03 — Metric contract V-ID

## Contract nghiệp vụ

| Nhóm | Metrics lab | Mapping production cần xác nhận |
|---|---|---|
| AuthN | `auth_*` | `identity-provider` native/step-up hoặc Hydra web completion |
| OTP | `otp_send_*`, `otp_delivery_*`, `otp_verify_*` | IdP route, Notification Center, GSM/WhatsApp và callback |
| OTP journey | `otp_journey_*`, `otp_stage_*` | Kong → IdP → Redis → routing → queue → provider boundary |
| Token | `token_*` | Hydra issuer, IdP transition issuer, `oauth2-token` front |
| HTTP | `http_request_*` | Kong và từng V-ID deployment/operation |
| AuthZ | `authorization_decisions_*` | `authz` enforce; denial là business result, không mặc định error |
| Dependency | database, queue, provider health | Redis/Postgres/Kafka/provider client instrumentation |

Tên `auth-service`, `otp-service`, `token-service` trong simulator là bounded
synthetic aliases để tạo dashboard. Chúng không phải tên component trong
`v-id-intern-docs`; production phải dùng `identity-provider`, `oauth2-server`,
`oauth2-token`, `authz`, `organization` và dependency name thực tế.

## OTP journey stages trong lab

```text
edge_to_kong → kong_to_idp → redis_challenge → route_selection
→ queue_wait → gsm_submit → carrier_delivery
```

`carrier_delivery` biểu diễn thời gian tới delivery receipt, không phải một HTTP
hop đồng bộ. Country là destination của OTP, không phải vị trí datacenter.

## Label policy

Cho phép khi bounded: `environment`, `cluster`, `service`, `operation`, `result`,
`reason`, `status_class`, `client_type`, `realm`, `issuer`, `grant_type`,
`channel`, `provider`, `destination_country`, `stage`.

Cấm trong Prometheus labels: phone/email, user/session/challenge/request/trace ID,
OTP, token, cookie, authorization code, raw URL có path parameter, error message
tự do và stack trace. Correlation ID chỉ nằm trong privacy-reviewed trace/log.

## Semantic

- Counter chỉ tăng và được query bằng `rate`/`increase`.
- Histogram dùng seconds, bucket được hiệu chỉnh từ dữ liệu thật.
- Gauge chỉ biểu diễn state hiện tại như queue depth/provider health.
- Failure reason dùng taxonomy hữu hạn: `invalid`, `expired`, `rate_limited`,
  `provider_error`, `dependency_error`, `timeout`, `internal_error`, `unknown`.
- Numerator luôn là tập con của denominator và cùng boundary/label aggregation.

## Cardinality và chất lượng

Ước tính `series ≈ tích cardinality labels × bucket/metric count`; kiểm tra HELP,
TYPE, unit suffix, counter reset, duplicate series, PII và no-data trước khi merge.
