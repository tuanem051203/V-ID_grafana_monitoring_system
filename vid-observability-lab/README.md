# V-ID Observability Lab

Workspace local/UAT chứa V-ID metrics simulator và observability stack để phát
triển, kiểm thử metric contract, recording rules, SLO dashboard và alert khi
metrics V-ID thật chưa sẵn sàng.

> Đây là baseline local/UAT theo hướng production, không phải production
> deployment. Các trường owner/target/route/runbook còn `TBD` hoặc
> `REPLACE-*` là release blocker và phải được thay thế trước khi release.

## Kiến trúc

```text
Metrics generator (5 giây) -> FastAPI /metrics    <- Prometheus <- Grafana
                              /health                |
                              /api/simulation        +--> Recording/alert rules
                                                         |
                                                         v
                                                    Alertmanager
```

Service không dùng database, Kafka hay OpenTelemetry. Counter chỉ tăng trong vòng
đời process. Traffic thay đổi mượt theo giờ, latency dùng phân phối log-normal và
incident tự kích hoạt rồi phục hồi mà không reset Counter.

## Cấu trúc repository

```text
vid-observability-lab/
├── services/
│   └── metrics-simulator/       # Deployable FastAPI component
│       ├── src/vid_mock_metrics/
│       ├── config/
│       ├── Dockerfile
│       └── pyproject.toml
├── observability/
│   ├── prometheus/              # Scrape, recording và alert rules
│   ├── grafana/                 # Dashboard và provisioning
│   └── alertmanager/            # Local/UAT routing
├── deployments/
│   └── local/docker-compose.yml # Chỉ dùng cho local/UAT
├── tests/
│   └── prometheus/              # Rule unit tests
├── docs/                        # KPI contract và runbook
└── scripts/                     # Validation entry points
```

Ranh giới này giúp CI chỉ build service khi `services/` thay đổi, validate rules
khi `observability/` thay đổi và giữ deployment profile tách khỏi source code.
Quyết định cấu trúc và phần còn thiếu cho production được ghi tại
[`docs/REPOSITORY-STRUCTURE.md`](docs/REPOSITORY-STRUCTURE.md).

## 6 KPI

| KPI                                  | Raw metric denominator                                | Target đề xuất     |
| ------------------------------------ | ----------------------------------------------------- | --------------------- |
| Authentication success               | `auth_success_total / auth_requests_total`          | >= 99.9% / 30d        |
| Authentication latency dưới 500 ms | bucket`le="0.5"` / histogram count                  | >= 95% / 30d          |
| OTP delivery success                 | `otp_delivery_success_total / otp_send_total`       | >= 95% / 30d          |
| OTP verification success             | `otp_verify_success_total / otp_verify_total`       | Baseline, chưa alert |
| Token issuance success               | `token_issue_total / token_request_total`           | >= 99.9% / 30d        |
| Platform availability                | `1 - http_requests_5xx_total / http_requests_total` | >= 99.9% / 30d        |

Định nghĩa đầy đủ, exclusion và quyết định còn phải được owner duyệt nằm trong
[`docs/KPI-CONTRACT.md`](docs/KPI-CONTRACT.md).

## Metrics

- Authentication: `auth_requests_total`, `auth_success_total`,
  `auth_failed_total`, `auth_request_duration_seconds`.
- OTP: `otp_send_total`, `otp_delivery_success_total`,
  `otp_delivery_failed_total`, `otp_verify_total`,
  `otp_verify_success_total`, `otp_verify_failed_total`.
- Token: `token_request_total`, `token_issue_total`, `token_failed_total`,
  `token_request_duration_seconds`.
- Platform: `http_requests_total`, `http_requests_5xx_total`,
  `http_request_duration_seconds`.
- Metric hỗ trợ: authorization, application error, infrastructure, pod,
  database, provider, queue và trạng thái simulation.

`environment` và `cluster` được Prometheus gắn từ scrape/service discovery.
Không có user ID, request ID, PII, raw URL hoặc label cardinality cao.
Các metric trên bao phủ tám nhóm Availability, Authentication, Performance,
Authorization, Traffic, Errors, Infrastructure và Database.

## Chạy local/UAT

```bash
export GRAFANA_ADMIN_PASSWORD='change-me'
export VID_LOAD_PROFILE='development'
docker compose -f deployments/local/docker-compose.yml up --build -d
docker compose -f deployments/local/docker-compose.yml ps
curl http://localhost:8000/health
curl http://localhost:8000/metrics
```

Các URL:

- Mock API: http://localhost:8000/docs
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000
- Alertmanager: http://localhost:9093

Prometheus datasource và năm dashboard được provision tự động:

- **V-ID — Overview**: KPI, trend, latency, traffic và symptom.
- **V-ID — Identity & Access**: authentication, OTP, token và authorization.
- **V-ID — Application Performance**: HTTP latency, traffic và application
  error.
- **V-ID — Infrastructure & Database**: tài nguyên node/pod, database latency,
  connection và error.
- **V-ID — SLO & Operations**: telemetry health, eligible traffic, error budget,
  burn rate và active alerts.

Datasource dùng UID ổn định `prometheus` và URL Docker nội bộ
`http://prometheus:9090`. Dashboard hỗ trợ filter `environment`, `cluster` và
giữ nguyên filter/time range khi chuyển qua các dashboard chi tiết.

Có thể chạy riêng mock service bằng Python 3.11+:

```bash
cd services/metrics-simulator
python -m venv .venv
source .venv/bin/activate
pip install -e .
PYTHONPATH=src uvicorn vid_mock_metrics.main:app --host 0.0.0.0 --port 8000
```

## Traffic profile và thời gian mô phỏng

```bash
VID_LOAD_PROFILE=uat \
  docker compose -f deployments/local/docker-compose.yml up --build -d
curl http://localhost:8000/api/simulation
```

Các profile `development`, `uat`, `production`, `peak` lần lượt có peak 20, 100,
500 và 2000 TPS. `VID_SIMULATION_DAY_SECONDS=3600` nén một ngày mô phỏng vào một
giờ để demo toàn bộ incident. Traffic curve, baseline và event nằm tại
`services/metrics-simulator/config/simulation.yaml`.

## PromQL

Mỗi KPI có cửa sổ `5m`, `1h`, `6h`, `24h`, `30d`:

```promql
vid:kpi_authentication_success:ratio5m * 100
vid:kpi_authentication_success:ratio30d * 100
vid:kpi_authentication_latency_under_500ms:ratio5m * 100
vid:kpi_otp_delivery_success:ratio5m * 100
vid:kpi_otp_verification_success:ratio5m * 100
vid:kpi_token_issuance_success:ratio5m * 100
vid:kpi_platform_availability:ratio5m * 100
```

Error budget và burn rate:

```promql
vid:slo_authentication_success:error_budget_remaining30d * 100
vid:slo_authentication_success:burnrate5m
```

Raw auth p95 cho eligible traffic:

```promql
histogram_quantile(
  0.95,
  sum by (le) (
    rate(auth_request_duration_seconds_bucket[5m])
  )
)
```

## Alert và runbook

Prometheus gửi alert tới Alertmanager. Local receiver cố ý không gửi thông báo
ra ngoài; production phải thay bằng integration on-call đã duyệt và lấy secret
từ secret manager. Alert có team, severity, service, dashboard URL và runbook
URL. Hướng xử lý nằm trong [`docs/RUNBOOK.md`](docs/RUNBOOK.md).

KPI-04 chỉ là baseline nên cố ý không có SLO burn-rate alert.

## Validation trước review

Máy validation cần Python 3.11+, Docker, `promtool` và `amtool`:

```bash
./scripts/validate.sh
```

Script kiểm tra Python syntax, dashboard JSON, Prometheus config/rules, sáu KPI
rule tests, Alertmanager config và Docker Compose. Không merge nếu validation
không đạt.

## Continuous Integration

GitHub Actions workflow tại `.github/workflows/ci.yml` chạy khi có Pull Request,
push vào `main` hoặc chạy thủ công. Pipeline gồm các quality gate độc lập:

- Ruff, Pyright, Python unit test và dependency audit.
- Dashboard JSON và dashboard contract test.
- Prometheus config/rules, `promtool` rule test và Alertmanager config.
- Docker Compose model validation.
- Build và quét lỗ hổng image bằng Trivy.
- Dựng toàn bộ stack, kiểm tra health endpoint, rule groups và Prometheus target.

Chạy các gate tương ứng trên máy phát triển:

```bash
pip install -e 'services/metrics-simulator[dev]'
./scripts/ci-python.sh
./scripts/ci-observability.sh
./scripts/ci-smoke-test.sh
```

`ci-observability.sh` và `ci-smoke-test.sh` cần Docker. Smoke test dùng Compose
project riêng và tự dọn container/volume của lần chạy đó khi hoàn tất.

## Production gate

1. Owner phê duyệt numerator, denominator, exclusion, target và window.
2. Đối chiếu metric thật, retry semantic, histogram bucket và cardinality.
3. Thay `local/docker-compose` bằng labels từ service discovery.
4. Bật SSO/RBAC/TLS; credential và notification secret không lưu trong Git.
5. Cấu hình HA, retention, persistent storage, backup và capacity.
6. Thay placeholder dashboard/runbook URL và cấu hình notification route.
7. Test normal, degradation, counter reset, no-data và low traffic.
8. Triển khai UAT, diễn tập lịch event, lưu evidence rồi mới promote production.

Dữ liệu mock không đại diện cho production baseline và không được dùng để tự
phê duyệt SLO hoặc capacity.
