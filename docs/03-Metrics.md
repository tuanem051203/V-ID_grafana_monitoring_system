# 03 — Thiết kế Metrics

## 1. Metric contract

Các metric dưới đây phục vụ phát triển và là contract đề xuất. Tên cuối cùng cần đối chiếu với code/service hiện có.

| Metric | Type | Labels | KPI |
|---|---|---|---|
| `vid_auth_attempts_total` | Counter | environment, service, result, realm, method | KPI-01 |
| `vid_auth_request_duration_seconds` | Histogram | environment, service, operation | KPI-02 |
| `vid_otp_delivery_total` | Counter | environment, channel, result, country, provider | KPI-03 |
| `vid_otp_verification_total` | Counter | environment, result, reason | KPI-04 |
| `vid_token_issuance_total` | Counter | environment, issuer, result, grant_type | KPI-05 |
| `vid_http_requests_total` | Counter | environment, service, operation, status_class | KPI-06 |

Metric bổ trợ:

| Metric | Type | Mục đích |
|---|---|---|
| `vid_dependency_up` | Gauge | Trạng thái dependency |
| `vid_dependency_request_duration_seconds` | Histogram | Dependency latency |
| `process_cpu_seconds_total` | Counter | CPU process |
| `process_resident_memory_bytes` | Gauge | Memory process |
| `kube_pod_container_status_restarts_total` | Counter | Pod restart |

## 2. Semantic

### Counter

- Chỉ tăng; reset khi process restart.
- Dùng `rate()` hoặc `increase()` để tính theo cửa sổ.
- Chỉ increment khi event đạt trạng thái đã định nghĩa.

### Histogram

Bucket gợi ý cho auth latency:

```text
0.05, 0.1, 0.2, 0.3, 0.5, 0.75, 1, 2, 5 giây
```

Bucket phải được hiệu chỉnh theo phân phối thật. Histogram cho phép aggregate giữa instance và tính percentile bằng `histogram_quantile`.

### Gauge

Chỉ dùng cho giá trị có thể tăng/giảm tại một thời điểm như dependency up hoặc queue depth. Không dùng gauge để mô hình hóa số request tích lũy.

## 3. Label policy

Labels được phép nếu tập giá trị hữu hạn:

- `environment`, `service`, `operation`
- `result`, `reason`, `status_class`
- `realm`, `method`, `channel`
- `country`, `provider`, `issuer`, `grant_type`

Labels bị cấm:

- `user_id`, `phone_number`, `email`
- `request_id`, `session_id`
- access/refresh token, OTP
- error message tự do, stack trace
- raw URL có path parameter

## 4. Result taxonomy

Đề xuất chuẩn hóa:

```text
auth result: success | failure
otp delivery result: delivered | failed
otp verification result: success | failure
token issuance result: success | failure
```

Failure reason là label riêng với danh mục hữu hạn:

```text
invalid | expired | rate_limited | provider_error |
dependency_error | timeout | internal_error | unknown
```

## 5. Ví dụ instrumentation

```text
vid_auth_attempts_total{
  environment="uat",
  service="identity-provider",
  result="success",
  realm="consumer",
  method="otp"
} 12345
```

```text
vid_http_requests_total{
  environment="uat",
  service="identity-provider",
  operation="login",
  status_class="2xx"
} 23456
```

## 6. Kiểm tra chất lượng metric

- Metric có `HELP` và `TYPE`.
- Unit nằm ở suffix: `_seconds`, `_bytes`, `_total`.
- Counter không giảm ngoài process restart.
- Không có duplicate series cùng label set.
- Không chứa PII/secret.
- Cardinality nằm trong budget.
- Tử số là tập con của mẫu số.
- Có dữ liệu trong môi trường kiểm thử và scrape không lỗi.

## 7. Cardinality budget

Trước khi thêm label, ước tính:

```text
series ≈ product(cardinality của từng label) × số metric/bucket
```

Histogram nhân số series theo số bucket. Với label như `client` hoặc `country`, cần đo cardinality thật và cân nhắc aggregate bằng recording rules.
