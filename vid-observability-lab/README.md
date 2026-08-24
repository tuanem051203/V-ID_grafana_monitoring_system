# V-ID Observability Lab

Workspace local/UAT chứa V-ID metrics simulator và observability stack để phát
triển, kiểm thử metric contract, recording rules, SLO dashboard và alert khi
metrics V-ID thật chưa sẵn sàng.

> Đây là baseline local/UAT theo hướng production, không phải production
> deployment. Các trường owner/target/route/runbook còn `TBD` hoặc
> `REPLACE-*` là release blocker và phải được thay thế trước khi release.

## Kiến trúc

```text
Metrics Simulator ── /metrics ──> Prometheus ──> rules ──> Alertmanager
       │                              │
       └─ OTLP traces (100% local/demo) ─> OTel Collector ─> Tempo
                                      │
Prometheus + Tempo ───────────────────┴──────────> Grafana
```

Service không dùng database hay Kafka thật. Counter chỉ tăng trong vòng đời
process; traffic/latency/incident đều synthetic. Simulator có OpenTelemetry để
phát OTP traces (100% trong local/demo), nhưng đây không phải context được truyền qua nhiều
process thật.

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
│   ├── config.json              # Deployment config theo environment
│   ├── config.schema.json
│   └── templates/               # Compose/Prometheus/Alertmanager/Grafana
├── generated/                   # Artifact được render, không commit
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
cp .env.example .env
# Thay các giá trị change-me trong .env trước khi chạy.
python3 scripts/render-config.py --environment local
docker compose --env-file .env -f generated/local/docker-compose.yml up --build -d
docker compose --env-file .env -f generated/local/docker-compose.yml ps
curl http://localhost:8000/health
curl http://localhost:8000/metrics
```

Các URL:

- Mock API: http://localhost:8000/docs
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000
- Alertmanager: http://localhost:9093
- Tempo API: http://localhost:3200

Prometheus datasource và 9 dashboard được provision tự động: Overview,
Authentication, MFA & OTP, OTP Journey, Token Lifecycle, Authorization, Platform
& Dependencies, SLO & Incidents và Cross-region Requests. Danh mục và mục đích
từng dashboard nằm tại `../docs/OBSERVABILITY.md`.

Cross-region simulator phát 10% platform traffic qua route giả lập và có kịch bản
suy giảm riêng. Destination country không chứng minh V-ID có datacenter hoặc
request thực sự đi qua quốc gia đó. Chi tiết metric, giới hạn dữ liệu và lộ trình
instrumentation thật nằm tại [`docs/CROSS-REGION-MONITORING.md`](docs/CROSS-REGION-MONITORING.md).

OTP journey simulator mô hình hóa luồng edge → Kong → IdP → Redis → routing →
queue → GSM → carrier. OpenTelemetry Collector và Tempo được khởi động cùng
stack; local/demo lưu 100% journey thành synthetic trace. Hướng dẫn demo và giới hạn
dữ liệu nằm tại [`docs/OTP-JOURNEY-MONITORING.md`](docs/OTP-JOURNEY-MONITORING.md).

Mapping production lấy từ `../docs/v-id-intern-docs`: IdP sở hữu OTP; browser
OIDC đi qua Hydra; `oauth2-token` đang chuyển thành Hydra front; `authz` thực hiện
RBAC và `organization` là organization source of truth. Các service name ngắn
trong simulator là synthetic aliases, không phải inventory production.

Datasource dùng UID ổn định `prometheus`; URL nội bộ được lấy từ
`deployments/config.json`. Dashboard mặc định chọn `All` cho `environment` và
`cluster`, vì vậy không bị khóa vào local khi promote sang môi trường khác.

## Cấu hình theo môi trường

`deployments/config.json` là nguồn sự thật cho image version, host port, scrape
target, label environment/cluster, Grafana datasource/public URL, runbook base
URL và Alertmanager SMTP/routing. Không sửa file trong `generated/` vì chúng sẽ
bị ghi đè ở lần render kế tiếp.

```bash
python3 scripts/render-config.py --environment local
python3 scripts/render-config.py --environment uat
python3 scripts/render-config.py --environment production
```

Mỗi lệnh sinh Compose, Prometheus config/rules, Alertmanager config, Grafana
datasource và `resolved.json` dưới `generated/<environment>/`. Password vẫn được
inject bằng Docker/Kubernetes Secret và không nằm trong JSON.

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
python3 scripts/render-config.py --environment uat
docker compose --env-file .env -f generated/uat/docker-compose.yml up --build -d
```

Các profile `development`, `uat`, `production`, `peak` lần lượt có peak 20, 100,
500 và 2000 TPS. `APP_ENV` chỉ chọn environment; toàn bộ profile, simulation day,
random seed, traffic curve, baseline và event nằm tại
`services/metrics-simulator/config/runtime.json`. Environment `peak` nén một ngày
mô phỏng vào một giờ. JSON Schema nằm cùng thư mục để kiểm tra cấu trúc.

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

Repository cung cấp các script quality gate để tích hợp vào CI của GitLab hoặc
nền tảng được owner lựa chọn. Hiện repository chưa version-control pipeline
definition; đây là production gate, không phải capability đã hoàn tất.

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
