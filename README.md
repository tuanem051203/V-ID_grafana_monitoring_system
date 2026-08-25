# V-ID Grafana Monitoring System

Hệ thống observability mẫu cho nền tảng định danh V-ID, được xây dựng để thiết
kế, mô phỏng và kiểm thử telemetry trước khi kết nối với môi trường UAT hoặc
production. Repository cung cấp metrics simulator, bộ thu thập và lưu trữ
metrics/logs/traces, dashboard Grafana, SLI/SLO, cảnh báo và tài liệu vận hành.

> **Trạng thái dự án:** local/UAT observability lab. Toàn bộ traffic, topology,
> metrics và OTP traces hiện tại là **synthetic**; các artifact trong repository
> chưa đồng nghĩa với việc hệ thống đã production-ready.

## 1. Mục tiêu dự án

Dự án giải quyết khoảng trống khi telemetry từ hệ thống V-ID thật chưa sẵn sàng:

- Chuẩn hóa metric contract cho các luồng xác thực, OTP, token, phân quyền và
  request nền tảng.
- Thống nhất cách tính KPI, SLI, SLO, error budget và burn rate.
- Xây dựng dashboard và alert có thể kiểm thử bằng dữ liệu mô phỏng.
- Mô hình hóa hành trình OTP end-to-end để drill-down từ metric sang trace.
- Chuẩn bị cấu hình có thể render lặp lại cho local, UAT và production profile.
- Cung cấp validation scripts, rule tests và runbook làm baseline cho quá trình
  tích hợp telemetry thật.

Nguồn chuẩn về domain và kiến trúc V-ID là
[`docs/v-id-intern-docs`](docs/v-id-intern-docs/README.md). Nếu mô hình trong lab
mâu thuẫn với tài liệu này, ưu tiên tài liệu domain và xác nhận lại với owner
trước khi thay đổi contract.

## 2. Phạm vi dự án

### Trong phạm vi

| Nhóm | Phạm vi được mô hình hóa |
|---|---|
| Authentication | Request, kết quả, nguyên nhân lỗi và latency của luồng đăng nhập/xác thực |
| MFA & OTP | Gửi OTP, delivery receipt, verification, provider, queue và latency theo từng stage |
| OAuth2/OIDC & token | Authorization flow, cấp/refresh/revoke token và giai đoạn chuyển đổi issuer |
| Authorization | Quyết định allow/deny/error theo organization-scoped RBAC |
| Platform | HTTP RED metrics, application error, pod/resource và dependency health |
| Reliability | 6 KPI chính, recording rules, SLO, error budget, burn-rate alert và no-data signal |
| Telemetry | Prometheus metrics, OpenTelemetry traces, structured synthetic logs và correlation |
| Visualization | Grafana dashboards cho overview, từng domain và điều tra sự cố |
| Deployment lab | Docker Compose được render theo profile local, UAT và production |
| Validation | Python tests, dashboard contract, Prometheus rule tests, config checks và smoke test |

Các component V-ID được dùng làm boundary gồm `identity-provider`, Ory Hydra
(`oauth2-server`), `oauth2-token`, `authz`, `organization`, Kong, Redis,
Postgres, Kafka và các notification/provider dependency. Các tên
`auth-service`, `otp-service`, `token-service` trong simulator chỉ là synthetic
alias, không phải inventory production.

### Ngoài phạm vi hiện tại

- Không kết nối database, Kafka, SMS provider hoặc workload V-ID thật.
- Không khẳng định baseline, capacity hay SLO production từ dữ liệu mock.
- Không cung cấp production Kubernetes/Helm/Kustomize deployment.
- Chưa triển khai HA, persistent storage, backup/disaster recovery và capacity
  planning cho observability stack.
- Chưa hoàn thiện SSO, RBAC, TLS, network policy và external secret manager.
- Chưa có CI/CD pipeline definition được version-control; repository mới cung
  cấp các quality-gate scripts để tích hợp vào nền tảng CI được lựa chọn.
- Các route cross-region là synthetic contract. `destination_country` là nơi
  nhận OTP/request mô phỏng, không chứng minh V-ID có datacenter tại quốc gia đó.
- Các owner, endpoint, notification route hoặc giá trị `TBD`/`REPLACE-*` phải
  được xác nhận trước khi release.

## 3. Kiến trúc giải pháp

```text
Metrics Simulator ── /metrics ──> Prometheus ── rules ──> Alertmanager
       │                              │
       └─ OTLP traces ──> OTel Collector ──> Tempo
       └─ structured logs ─────────────────> Loki
                                      │
Prometheus + Tempo + Loki ────────────┴──────────> Grafana
```

Luồng OTP được mô hình hóa theo các stage:

```text
edge → Kong → identity-provider → Redis → route selection
     → queue → GSM/provider submit → carrier delivery receipt
```

Prometheus lưu metrics và thực thi recording/alert rules; Alertmanager routing
cảnh báo; OpenTelemetry Collector chuyển trace sang Tempo; Loki lưu log mô
phỏng; Grafana cung cấp một điểm quan sát chung và liên kết metric-to-trace cho
OTP journey.

## 4. Các phần đã hoàn thành

Các con số dưới đây được lấy từ artifact đang version-control, không phải tuyên
bố production readiness.

| Hạng mục | Kết quả hiện có | Trạng thái |
|---|---|---|
| Domain discovery | Snapshot architecture, component, gateway routing, eKYC, AuthZ và OAuth flows | Hoàn thành baseline tài liệu |
| Metrics simulator | FastAPI sinh AuthN, OTP, token, AuthZ, HTTP, dependency metrics, traffic profile và incident scenario | Đã triển khai cho lab |
| KPI/SLI/SLO | 6 KPI chính, nhiều time window, error budget và burn rate | Đã triển khai; target chờ owner duyệt |
| Prometheus rules | **62 recording rules** và **17 alert rules** | Đã triển khai và có rule tests |
| Grafana | **9 dashboards / 83 panels**, datasource và dashboard provisioning tự động | Đã triển khai |
| OTP observability | Stage metrics, latency/error signals, sampled traces và metric-to-trace drill-down | Đã triển khai synthetic |
| Cross-region | Synthetic route metrics, dashboard, rules và degradation scenario | Đã triển khai synthetic |
| Alerting | Alertmanager template, severity/team labels, dashboard/runbook link và local/UAT routing | Đã triển khai baseline |
| Deployment profiles | Renderer và resolved Compose artifacts cho `local`, `uat`, `production` | Đã triển khai; production profile chưa phải production deployment |
| Validation | Python unit test, dashboard contract, JSON/config validation, `promtool`, `amtool`, Compose check và smoke scripts | Đã triển khai quality gates |
| Operations docs | KPI contract, telemetry strategy, OTP/cross-region guide, repository decision và incident runbook | Đã hoàn thành baseline |

### Dashboard hiện có

1. V-ID SSO — Tổng quan
2. V-ID SSO — Đăng nhập & Xác thực
3. V-ID SSO — MFA & OTP
4. V-ID SSO — OTP Journey
5. V-ID SSO — Token Lifecycle
6. V-ID SSO — Phân quyền & Truy cập
7. V-ID SSO — Nền tảng & Phụ thuộc
8. V-ID SSO — SLO & Sự cố
9. V-ID SSO — Cross-region Requests

### 6 KPI chính

| KPI | Cách đo trong lab | Target đề xuất |
|---|---|---|
| Authentication success | `auth_success_total / auth_requests_total` | ≥ 99.9% / 30 ngày |
| Authentication latency | Tỷ lệ request có latency ≤ 500 ms | ≥ 95% / 30 ngày |
| OTP delivery success | `otp_delivery_success_total / otp_send_total` | ≥ 95% / 30 ngày |
| OTP verification success | `otp_verify_success_total / otp_verify_total` | Baseline, chưa alert SLO |
| Token issuance success | `token_issue_total / token_request_total` | ≥ 99.9% / 30 ngày |
| Platform availability | `1 - http_requests_5xx_total / http_requests_total` | ≥ 99.9% / 30 ngày |

Định nghĩa numerator, denominator, exclusion và boundary chi tiết nằm trong
[`KPI-CONTRACT.md`](vid-observability-lab/docs/KPI-CONTRACT.md). Các target trên
chỉ phục vụ kiểm thử và cần được product/service owner phê duyệt bằng dữ liệu UAT.

## 5. Cấu trúc repository

```text
.
├── README.md                         # Tổng quan, scope và trạng thái dự án
├── docs/
│   ├── README.md                     # Bản đồ tài liệu
│   ├── OBSERVABILITY.md              # Observability handbook
│   └── v-id-intern-docs/             # Nguồn domain V-ID
└── vid-observability-lab/
    ├── services/metrics-simulator/   # FastAPI synthetic telemetry service
    ├── observability/
    │   ├── prometheus/               # Scrape config, recording/alert rules
    │   ├── grafana/                  # Dashboard và provisioning
    │   └── alertmanager/             # Alert routing baseline
    ├── deployments/                  # Config, schema và templates
    ├── generated/                    # Artifact sinh từ renderer, không sửa tay
    ├── tests/                        # Dashboard contract và Prometheus tests
    ├── scripts/                      # Render, validate, CI và smoke test
    ├── docs/                         # Contract, strategy và runbook
    └── secrets/                      # Hướng dẫn quản lý secret
```

## 6. Chạy dự án trên local

### Yêu cầu

- Python 3.11+
- Docker Engine và Docker Compose plugin
- `promtool` và `amtool` nếu chạy toàn bộ validation

### Khởi động stack

```bash
cd vid-observability-lab
cp .env.example .env
# Thay toàn bộ giá trị change-me trong .env.
python3 scripts/render-config.py --environment local
docker compose --env-file .env -f generated/local/docker-compose.yml up --build -d
docker compose --env-file .env -f generated/local/docker-compose.yml ps
```

### Endpoint local

| Thành phần | URL |
|---|---|
| Metrics Simulator / Swagger | http://localhost:8000/docs |
| Simulator health | http://localhost:8000/health |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 |
| Alertmanager | http://localhost:9093 |
| Tempo API | http://localhost:3200 |
| Loki API | http://localhost:3100 |

Grafana datasource và toàn bộ dashboard được provision tự động. Credential lấy
từ `.env`; không commit secret vào repository.

### Dừng stack

```bash
docker compose --env-file .env -f generated/local/docker-compose.yml down
```

## 7. Cấu hình theo môi trường

[`deployments/config.json`](vid-observability-lab/deployments/config.json) là
nguồn cấu hình tập trung cho image version, port, scrape interval, retention,
sampling, alert threshold, datasource, public URL và Alertmanager routing.

```bash
cd vid-observability-lab
python3 scripts/render-config.py --environment local
python3 scripts/render-config.py --environment uat
python3 scripts/render-config.py --environment production
```

Mỗi lệnh sinh cấu hình đã resolve dưới `generated/<environment>/`. Không chỉnh
sửa trực tiếp thư mục `generated/`, vì nội dung sẽ bị ghi đè ở lần render sau.
Các profile UAT/production hiện chứa placeholder và vẫn cần tích hợp với secret
manager, service discovery và hạ tầng thật.

## 8. Kiểm thử và validation

```bash
cd vid-observability-lab
./scripts/validate.sh
```

Validation bao gồm render mọi environment, unit test simulator, dashboard
contract, JSON validation, kiểm tra Prometheus/Alertmanager, rule tests cho KPI,
OTP journey và cross-region, cùng Docker Compose config check.

Các gate tách riêng để tích hợp CI:

```bash
./scripts/ci-python.sh
./scripts/ci-observability.sh
./scripts/ci-smoke-test.sh
```

## 9. Lộ trình để kết nối UAT/production

1. Xác nhận owner cho từng service, KPI, dashboard, alert và runbook.
2. Chốt numerator, denominator, exclusion, SLO target và evaluation window.
3. Ánh xạ synthetic metric sang telemetry thật của Kong, IdP, Hydra, AuthZ,
   Redis, Kafka, database và provider.
4. Xác nhận retry, OTP acceptance/delivery receipt và token issuer semantics.
5. Thay static target bằng service discovery phù hợp với nền tảng triển khai.
6. Hoàn thiện SSO/RBAC/TLS, secret manager, network policy và notification route.
7. Thiết kế HA, storage, retention, backup, capacity và disaster recovery.
8. Test normal, degradation, no-data, low traffic, counter reset và rollback.
9. Thu thập UAT evidence, hiệu chỉnh threshold rồi mới phê duyệt production.
10. Bổ sung CI/CD, release versioning, approval policy và deployment manifest.

## 10. Tài liệu liên quan

- [Bản đồ tài liệu](docs/README.md)
- [V-ID Observability Handbook](docs/OBSERVABILITY.md)
- [Hướng dẫn vận hành lab](vid-observability-lab/README.md)
- [KPI contract](vid-observability-lab/docs/KPI-CONTRACT.md)
- [Telemetry strategy](vid-observability-lab/docs/TELEMETRY-STRATEGY.md)
- [OTP journey monitoring](vid-observability-lab/docs/OTP-JOURNEY-MONITORING.md)
- [Cross-region monitoring](vid-observability-lab/docs/CROSS-REGION-MONITORING.md)
- [Incident runbook](vid-observability-lab/docs/RUNBOOK.md)

## 11. Nguyên tắc an toàn dữ liệu

- Không dùng phone, email, user/session/request/trace ID, OTP, token, cookie hoặc
  authorization code làm Prometheus label.
- Không lưu PII, credential hoặc secret trong dashboard, config hay Git history.
- Chỉ dùng bounded labels đã được review để kiểm soát cardinality.
- Dữ liệu synthetic không được dùng để tự phê duyệt SLO, capacity hoặc quyết
  định production.
