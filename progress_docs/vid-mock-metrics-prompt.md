# Prompt xây dựng Mock Metrics cho V-ID

## Mục tiêu

Xây dựng project **`vid-mock-metrics`** dùng để giả lập Prometheus
metrics cho hệ thống V-ID khi chưa thể truy cập metrics thật.

### Công nghệ

-   Python 3.11+
-   FastAPI
-   prometheus-client
-   Docker
-   Docker Compose

Service cần:

-   Chạy tại port **8000**
-   Có endpoint **/health**
-   Có endpoint **/metrics** theo chuẩn Prometheus
-   Sinh metrics liên tục theo thời gian
-   Hỗ trợ nhiều kịch bản (scenario)
-   Được Prometheus scrape mỗi 5 giây
-   Không dùng Database
-   Không dùng Kafka hoặc OpenTelemetry

------------------------------------------------------------------------

# 6 KPI cần mô phỏng

  KPI      Mô tả                              Target
  -------- ---------------------------------- ----------
  KPI-01   Authentication Success Rate        ≥99.9%
  KPI-02   Authentication Latency (\<500ms)   ≥95%
  KPI-03   OTP Delivery Success Rate          ≥95%
  KPI-04   OTP Verification Success Rate      Baseline
  KPI-05   Token Issuance Success Rate        ≥99.9%
  KPI-06   Platform Availability              ≥99.9%

------------------------------------------------------------------------

# Metrics cần tạo

## Authentication

Counter

``` text
vid_auth_requests_total
```

Labels

``` text
result=success|failed
valid=true|false
client_type=terminal|mobile|web
reason=none|invalid_credential|locked|expired|system_error
```

Histogram

``` text
vid_auth_request_duration_seconds
```

Buckets

``` text
0.05
0.1
0.2
0.3
0.5
0.75
1
2
5
```

------------------------------------------------------------------------

## OTP Delivery

Counter

``` text
vid_otp_send_attempts_total
```

Labels

``` text
result=delivered|failed|pending
provider=viettel|vnpt|mock
channel=sms|email
reason=none|provider_error|invalid_destination|timeout|rate_limited
```

------------------------------------------------------------------------

## OTP Verification

Counter

``` text
vid_otp_verification_attempts_total
```

Labels

``` text
result=success|failed
valid=true|false
channel=sms|email
reason=none|wrong_otp|expired_otp|max_attempts|system_error
```

------------------------------------------------------------------------

## Token

Counter

``` text
vid_token_requests_total
```

Labels

``` text
result=issued|failed
valid=true|false
token_type=access_token|refresh_token|id_token
grant_type=authorization_code|refresh_token|client_credentials
reason=none|invalid_grant|signing_error|storage_error|system_error
```

------------------------------------------------------------------------

## Platform Availability

Counter

``` text
vid_http_requests_total
```

Labels

``` text
service=auth-service|otp-service|token-service
endpoint=/authenticate|/otp/send|/otp/verify|/token|/token/refresh
method=POST
status_code=200|400|401|429|500|503
critical=true|false
```

------------------------------------------------------------------------

## Gauge

``` text
vid_auth_requests_in_progress
vid_otp_queue_size
vid_token_requests_in_progress
vid_otp_provider_status
```

------------------------------------------------------------------------

# Cấu trúc Project

``` text
vid-mock-metrics/
├── app/
│   ├── main.py
│   ├── metrics.py
│   ├── generator.py
│   ├── scenarios.py
│   └── config.py
├── config/
│   └── scenarios.yaml
├── prometheus/
│   ├── prometheus.yml
│   └── rules/
│       └── vid-kpi-rules.yml
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

------------------------------------------------------------------------

# Scenarios

-   normal
-   auth_slow
-   otp_provider_incident
-   platform_incident

Cho phép đổi scenario qua:

``` text
POST /api/scenario/{scenario_name}
```

Không được reset Counter khi đổi scenario.

------------------------------------------------------------------------

# API

    GET /health
    GET /metrics
    GET /api/scenario
    POST /api/scenario/{scenario}

------------------------------------------------------------------------

# Logic sinh dữ liệu

-   Sinh dữ liệu mỗi 5 giây
-   Counter chỉ tăng
-   Histogram dùng observe()
-   Gauge tăng giảm theo trạng thái
-   Latency \<500ms hoặc \>500ms theo tỷ lệ của scenario
-   Không random hoàn toàn
-   Không dùng label cardinality cao (user_id, request_id...)

------------------------------------------------------------------------

# Prometheus

Scrape interval:

``` yaml
5s
```

Tạo Recording Rules cho:

-   Authentication Success
-   Authentication Latency
-   OTP Delivery
-   OTP Verification
-   Token Issuance
-   Platform Availability

------------------------------------------------------------------------

# Docker Compose

Triển khai:

-   vid-mock-metrics
-   Prometheus
-   Grafana

Không sử dụng trường `version`.

------------------------------------------------------------------------

# README

Bao gồm:

1.  Kiến trúc
2.  6 KPI
3.  Danh sách metrics
4.  Hướng dẫn chạy
5.  PromQL mẫu
6.  Chuyển scenario
7.  URL Prometheus/Grafana
8.  Giải thích dữ liệu mock

------------------------------------------------------------------------

# Yêu cầu code

-   Chạy được ngay
-   Type hint
-   Logging
-   Error handling
-   Clean Architecture
-   Không duplicated code
-   Đúng Prometheus naming convention
-   `_seconds` cho duration
-   `_total` cho Counter
-   Không tạo label cardinality cao

------------------------------------------------------------------------

# Yêu cầu AI

Thực hiện theo thứ tự:

1.  Tạo toàn bộ cấu trúc thư mục.
2.  Sinh đầy đủ source code cho từng file.
3.  Viết Dockerfile.
4.  Viết Docker Compose.
5.  Viết Prometheus config.
6.  Viết Recording Rules.
7.  Viết README.
8.  Kiểm tra lỗi cú pháp.
9.  Đưa ra lệnh chạy.
10. Không chỉ giải thích mà phải tạo đầy đủ project hoàn chỉnh.
