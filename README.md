# V-ID Grafana Monitoring System

Observability lab cho nền tảng V-ID, được thiết kế dựa trên tài liệu nội bộ trong
[`docs/v-id-intern-docs`](docs/v-id-intern-docs/README.md). Lab dùng Prometheus,
Grafana, Alertmanager, OpenTelemetry Collector và Tempo để mô phỏng metrics/traces
cho authentication, OTP, token, authorization và dependency health.

## Kiến trúc V-ID được dùng làm chuẩn

- `identity-provider`: identity broker, OTP, session/profile và login/consent UI.
- Ory Hydra (`oauth2-server`): OAuth2/OIDC; target ADR-0007 là sole issuer.
- `oauth2-token`: transition token router, target là Hydra front.
- `authz` và `organization`: organization-scoped authorization plane.
- Kong, Redis, Postgres, Kafka và các external dependencies.
- Notification Center; GSM/WhatsApp routing cho international OTP theo policy.

`account` đang decommission và dev/prod gateway chưa hoàn toàn đồng nhất. Native
V-App SMS OTP flow được giữ để mô tả transition nhưng đã deprecated theo ADR-0007.

## Lab topology

```text
Metrics Simulator ──metrics──> Prometheus ──rules──> Alertmanager
       │                            │
       └─ sampled OTLP traces ─> OTel Collector ─> Tempo
                                    │
Prometheus + Tempo ─────────────────┴────────────> Grafana
```

International OTP demo:

```text
edge → Kong → identity-provider → Redis → route selection
→ Notification Center queue → GSM submit → carrier delivery receipt
```

Country ở đây là nơi nhận OTP, không phải bằng chứng có V-ID datacenter tại quốc
gia đó. Dashboard generic cross-region là synthetic test contract riêng.

## Chạy local

```bash
cd vid-observability-lab
python3 scripts/render-config.py --environment local
GRAFANA_ADMIN_PASSWORD=admin VID_SMTP_APP_PASSWORD=unused \
  docker compose -f generated/local/docker-compose.yml up --build -d
```

- Grafana: [http://localhost:3000](http://localhost:3000)
- Prometheus: http://localhost:9090
- Alertmanager: [http://localhost:9093](http://localhost:9093)
- Tempo API: [http://localhost:3200](http://localhost:3200)
- Simulator/OpenAPI: [http://localhost:8000/docs](http://localhost:8000/docs)

## Tài liệu

1. [Tổng quan](docs/01-Overview.md)
2. [KPI/SLI/SLO](docs/02-KPI-SLI-SLO.md)
3. [Metric contract](docs/03-Metrics.md)
4. [Prometheus](docs/04-Prometheus.md)
5. [Grafana](docs/05-Grafana.md)
6. [Alerting](docs/06-Alerting.md)
7. [GitOps](docs/08-GitOps.md)
8. [Deployment](docs/09-Deployment.md)
9. [OTP journey demo](vid-observability-lab/docs/OTP-JOURNEY-MONITORING.md)

## Ranh giới sử dụng

Metrics, topology, SLO và traces hiện tại là synthetic. Trước khi đưa lên UAT,
service/network owner phải xác nhận route, instrumentation, label contract,
threshold, privacy, retention và notification ownership bằng deployment/dữ liệu
thật. Living V-ID docs luôn được ưu tiên hơn snapshot trong repository.
