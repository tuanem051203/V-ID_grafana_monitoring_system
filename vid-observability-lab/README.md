# V-ID Observability Lab

Workspace local/UAT chứa V-ID metrics simulator và observability stack để phát
triển, kiểm thử metric contract, recording rules, SLO dashboard và alert khi
metrics V-ID thật chưa sẵn sàng.

> Đây là baseline local/UAT theo hướng production, không phải production
> deployment. Các trường owner/target/route/runbook còn `TBD` hoặc
> `REPLACE-*` là release blocker và phải được thay thế trước khi release.

## Kiến trúc

```text
Metrics generator (5 giây) -> FastAPI /metrics <- Prometheus <- Grafana
                              /health             |
                              /api/scenario       +--> Recording/alert rules
                                                         |
                                                         v
                                                    Alertmanager
```

Service không dùng database, Kafka hay OpenTelemetry. Counter chỉ tăng trong vòng
đời process; đổi scenario không reset Counter. Dữ liệu được phân bổ theo tỷ lệ
cấu hình và dao động gauge theo chu kỳ thay vì random hoàn toàn.

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

| KPI | Eligible denominator | Target đề xuất |
|---|---|---|
| Authentication success | success + technical `system_error`; loại business rejection | >= 99.9% / 30d |
| Authentication latency dưới 500 ms | eligible auth histogram count | >= 95% / 30d |
| OTP delivery success | delivered + provider/timeout failure; loại pending/client error | >= 95% / 30d |
| OTP verification success | mọi terminal attempt | Baseline, chưa alert |
| Token issuance success | issued + signing/storage/system failure; loại invalid grant | >= 99.9% / 30d |
| Platform availability | critical terminal request | >= 99.9% / 30d |

Định nghĩa đầy đủ, exclusion và quyết định còn phải được owner duyệt nằm trong
[`docs/KPI-CONTRACT.md`](docs/KPI-CONTRACT.md).

## Metrics

- Counter: `vid_auth_requests_total`, `vid_otp_send_attempts_total`,
  `vid_otp_verification_attempts_total`, `vid_token_requests_total`,
  `vid_http_requests_total`.
- Histogram: `vid_auth_request_duration_seconds` với label bounded `result`,
  `client_type`, `reason` và bucket `0.05`, `0.1`, `0.2`, `0.3`, `0.5`,
  `0.75`, `1`, `2`, `5`.
- Gauge: `vid_auth_requests_in_progress`, `vid_otp_queue_size`,
  `vid_token_requests_in_progress`, `vid_otp_provider_status`.

`environment` và `cluster` được Prometheus gắn từ scrape/service discovery.
Không có user ID, request ID, PII, raw URL hoặc label cardinality cao.

## Chạy local/UAT

```bash
export GRAFANA_ADMIN_PASSWORD='change-me'
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

Prometheus datasource và hai dashboard được provision tự động:

- **V-ID — 6 KPI Overview**: KPI, trend, latency, traffic và symptom.
- **V-ID — SLO & Operations**: telemetry health, eligible traffic, error budget,
  burn rate và active alerts.

Datasource dùng UID ổn định `prometheus` và URL Docker nội bộ
`http://prometheus:9090`. Dashboard hỗ trợ filter `environment` và `cluster`.

Có thể chạy riêng mock service bằng Python 3.11+:

```bash
cd services/metrics-simulator
python -m venv .venv
source .venv/bin/activate
pip install -e .
PYTHONPATH=src uvicorn vid_mock_metrics.main:app --host 0.0.0.0 --port 8000
```

## Scenario

Các profile: `normal`, `auth_slow`, `otp_provider_incident`,
`platform_incident`.

```bash
curl http://localhost:8000/api/scenario
curl -X POST http://localhost:8000/api/scenario/auth_slow
curl -X POST http://localhost:8000/api/scenario/normal
```

Đổi scenario không reset Counter. Scenario không hợp lệ trả HTTP 404. Cấu hình
lưu lượng/tỷ lệ nằm tại
`services/metrics-simulator/config/scenarios.yaml`.

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
    rate(vid_auth_request_duration_seconds_bucket{
      reason=~"none|system_error"
    }[5m])
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

## Production gate

1. Owner phê duyệt numerator, denominator, exclusion, target và window.
2. Đối chiếu metric thật, retry semantic, histogram bucket và cardinality.
3. Thay `local/docker-compose` bằng labels từ service discovery.
4. Bật SSO/RBAC/TLS; credential và notification secret không lưu trong Git.
5. Cấu hình HA, retention, persistent storage, backup và capacity.
6. Thay placeholder dashboard/runbook URL và cấu hình notification route.
7. Test normal, degradation, counter reset, no-data và low traffic.
8. Triển khai UAT, diễn tập scenario, lưu evidence rồi mới promote production.

Dữ liệu mock không đại diện cho production baseline và không được dùng để tự
phê duyệt SLO hoặc capacity.
