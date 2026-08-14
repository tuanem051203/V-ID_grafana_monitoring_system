# V-ID Grafana Monitoring System

Observability lab cho nền tảng V-ID. Dự án dùng dữ liệu synthetic để thiết kế và
kiểm thử metric contract, dashboard, SLO, alert và trace trước khi kết nối UAT.

> [`docs/v-id-intern-docs`](docs/v-id-intern-docs/README.md) là nguồn chuẩn về
> V-ID. Khi có mâu thuẫn, ưu tiên nguồn này và xác nhận living document/owner.

## Dự án hiện có gì?

| Khối | Hiện trạng | Điểm vào |
|---|---|---|
| V-ID domain snapshot | Architecture, component inventory, routing, eKYC, AuthZ và OAuth flows | [V-ID start here](docs/v-id-intern-docs/docs/00-start-here.md) |
| Metrics Simulator | FastAPI sinh AuthN, OTP, token, AuthZ, HTTP, dependency metrics và sampled OTP traces | [Simulator](vid-observability-lab/services/metrics-simulator/README.md) |
| Metrics & SLO | Prometheus config, **62 recording rules**, rule tests và exemplar storage | [Observability handbook](docs/OBSERVABILITY.md) |
| Visualization | **9 Grafana dashboards / 83 panels** | [Dashboards](vid-observability-lab/observability/grafana/dashboards) |
| Alerting | **17 alert rules**, Alertmanager template và runbook | [Runbook](vid-observability-lab/docs/RUNBOOK.md) |
| Tracing | OpenTelemetry Collector, Tempo và metrics-to-trace cho OTP journey | [OTP journey](vid-observability-lab/docs/OTP-JOURNEY-MONITORING.md) |
| Deployment | Renderer cho local, UAT và production profile | [Lab README](vid-observability-lab/README.md) |
| Validation | Python tests, dashboard contract, rule tests và smoke scripts | [Scripts](vid-observability-lab/scripts) |

Các con số phản ánh artifact đang version-control, không phải production readiness.
Xem [Documentation map](docs/README.md) để chọn đúng tài liệu theo câu hỏi.

## V-ID boundary được mô hình hóa

- `identity-provider`: identity broker, OTP, profile/session, login/consent UI.
- Ory Hydra (`oauth2-server`): OAuth2/OIDC; ADR-0007 hướng tới sole issuer.
- `oauth2-token`: transition token router, hướng tới Hydra front.
- `authz` và `organization`: organization-scoped authorization plane.
- Kong, Redis, Postgres, Kafka và notification/provider dependencies.
- `account` đang decommission; dev/prod gateway chưa hoàn toàn đồng nhất.

Các alias `auth-service`, `otp-service`, `token-service` chỉ dùng để sinh dữ liệu,
không phải inventory workload production.

## Luồng lab

```text
Metrics Simulator ──metrics──> Prometheus ──rules──> Alertmanager
       │                            │
       └─ sampled OTLP traces ─> OTel Collector ─> Tempo
                                    │
Prometheus + Tempo ─────────────────┴────────────> Grafana
```

OTP journey: `edge → Kong → identity-provider → Redis → route selection → queue
→ GSM submit → carrier delivery receipt`. Country là nơi nhận OTP, không phải
bằng chứng có V-ID datacenter tại quốc gia đó. Cross-region là synthetic contract.

## Đọc theo nhu cầu

- Mới vào dự án: [Documentation map](docs/README.md) → [V-ID start here](docs/v-id-intern-docs/docs/00-start-here.md) → [Observability handbook](docs/OBSERVABILITY.md).
- Chạy demo: [Lab README](vid-observability-lab/README.md).
- Review KPI: [KPI contract](vid-observability-lab/docs/KPI-CONTRACT.md).
- Điều tra sự cố: [Runbook](vid-observability-lab/docs/RUNBOOK.md).
- Hiểu synthetic journeys: [OTP](vid-observability-lab/docs/OTP-JOURNEY-MONITORING.md) và [cross-region](vid-observability-lab/docs/CROSS-REGION-MONITORING.md).

## Chạy nhanh local

```bash
cd vid-observability-lab
cp .env.example .env
# Thay toàn bộ giá trị change-me trong .env.
python3 scripts/render-config.py --environment local
docker compose --env-file .env -f generated/local/docker-compose.yml up --build -d
```

Grafana `:3000` · Prometheus `:9090` · Alertmanager `:9093` · Tempo `:3200` · Simulator `:8000/docs`.

## Ranh giới sử dụng

Metrics, topology, SLO và traces hiện tại đều synthetic. Trước UAT/production,
owner phải xác nhận route, instrumentation, labels, thresholds, privacy,
retention, notification ownership, HA và rollback bằng deployment/dữ liệu thật.
