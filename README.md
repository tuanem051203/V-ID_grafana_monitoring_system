# V-ID Grafana Monitoring System

Hệ thống monitoring cho nền tảng định danh V-ID, tập trung vào trải nghiệm đăng nhập, OTP, phát hành OAuth2/OIDC token và độ sẵn sàng của các dịch vụ identity core.

Dự án sử dụng **Prometheus**, **Grafana** và **Alertmanager** để:

- Thu thập metric từ các dịch vụ V-ID.
- Tính toán KPI, SLI và mức tuân thủ SLO.
- Hiển thị sức khỏe nền tảng trên Grafana.
- Cảnh báo sớm khi dịch vụ suy giảm hoặc tiêu thụ error budget quá nhanh.
- Quản lý dashboard và rules bằng Git.

> Repository đang trong giai đoạn thiết kế và phát triển. Metric contract, SLO target, datasource UID, notification route và thông tin môi trường phải được xác nhận với V-ID service owner/SRE trước khi triển khai UAT.

## Bối cảnh

V-ID là nền tảng đăng nhập và định danh dùng chung cho các ứng dụng trong hệ sinh thái Vingroup. Luồng xác thực chính:

```text
PnL App / V-ID SDK
        |
        v
Kong Gateway
        |
        v
identity-provider ----> OTP Provider
        |
        v
Hydra / oauth2-token
        |
        v
Application Session
```

Đây là luồng Tier-1. Hệ thống monitoring cần giúp đội vận hành trả lời nhanh:

- Người dùng có đăng nhập được không?
- OTP có được gửi và xác minh thành công không?
- Token có được phát hành ổn định không?
- Latency có đáp ứng mục tiêu không?
- Service, dependency hoặc nhóm traffic nào đang gây lỗi?
- SLO và error budget đang ở trạng thái nào?

## Kiến trúc monitoring

```text
V-ID Services / Dependencies
        |
        | /metrics
        v
Prometheus
  |     |
  |     +--> Recording Rules
  |     +--> Alert Rules
  |               |
  |               v
  |          Alertmanager
  |               |
  |               v
  |       On-call / Notification
  v
Grafana
  |
  +--> KPI Overview
  +--> Authentication / OTP / Token
  +--> SLO / Error Budget
  +--> Service / Dependency Health
```

Luồng xử lý:

1. V-ID services xuất metric qua endpoint `/metrics`.
2. Prometheus scrape và lưu time series.
3. Recording rules tính trước rate, ratio, latency và SLI.
4. Grafana truy vấn raw metrics hoặc recorded series để hiển thị.
5. Alert rules đánh giá lỗi, latency và SLO burn rate.
6. Alertmanager group, route và gửi cảnh báo tới kênh vận hành.
7. On-call sử dụng dashboard và runbook để điều tra, giảm thiểu ảnh hưởng.

## Sáu KPI chính

| ID | KPI | Ý nghĩa |
|---|---|---|
| KPI-01 | Authentication success rate | Tỷ lệ đăng nhập hoàn tất thành công |
| KPI-02 | Authentication latency | Thời gian xử lý authentication, tập trung p95/SLO threshold |
| KPI-03 | OTP delivery success rate | Tỷ lệ OTP được delivery thành công |
| KPI-04 | OTP verification success rate | Tỷ lệ xác minh OTP thành công |
| KPI-05 | Token issuance success rate | Tỷ lệ phát hành OAuth2/OIDC token thành công |
| KPI-06 | Platform availability | Tỷ lệ critical request không gặp lỗi hệ thống |

Target trong tài liệu hiện là đề xuất ban đầu. Trước khi áp dụng tại UAT cần:

- Xác nhận numerator, denominator và exclusions.
- Phân biệt technical failure, business rejection và user error.
- Phân tích baseline bằng dữ liệu thật.
- Chốt target, window và alert severity với service owner.

## Công nghệ

- Prometheus
- PromQL
- Prometheus recording rules và alert rules
- Alertmanager
- Grafana
- Python 3.11+ và Flask cho local mock exporter
- Git/GitOps
- `promtool` cho validation và rule unit tests

## Cấu trúc repository

```text
.
├── README.md
├── PROJECT_PLAN.md
├── V-ID_Mock_Metrics_Guide.md
├── docs/
│   ├── README.md
│   ├── 01-Overview.md
│   ├── 02-KPI-SLI-SLO.md
│   ├── 03-Metrics.md
│   ├── 04-Prometheus.md
│   ├── 05-Grafana.md
│   ├── 06-Alerting.md
│   ├── 08-GitOps.md
│   └── 09-Deployment.md
└── mock-exporter/
    ├── README.md
    ├── requirements.txt
    └── mock_metrics.py
```

Các artifact dự kiến bổ sung trong những giai đoạn tiếp theo:

```text
grafana/
  dashboards/
    vid-kpis.json
prometheus/
  rules/
    vid-kpi-recording-rules.yaml
    vid-kpi-alerts.yaml
  tests/
    vid-kpi-rules.test.yaml
scripts/
  validate.ps1
```

## Tài liệu

Bắt đầu tại [docs/README.md](docs/README.md):

1. [Overview](docs/01-Overview.md) — kiến trúc monitoring và phạm vi.
2. [KPI, SLI và SLO](docs/02-KPI-SLI-SLO.md) — định nghĩa sáu KPI.
3. [Metrics](docs/03-Metrics.md) — metric contract và label policy.
4. [Prometheus](docs/04-Prometheus.md) — scrape, recording và alert rules.
5. [Grafana](docs/05-Grafana.md) — dashboard và visualization.
6. [Alerting](docs/06-Alerting.md) — alert strategy và runbook.
7. [GitOps](docs/08-GitOps.md) — quản lý artifact bằng Git.
8. [Deployment](docs/09-Deployment.md) — quy trình triển khai và kiểm thử UAT.

Kế hoạch công việc chi tiết và cách chia task cho Codex nằm tại [PROJECT_PLAN.md](PROJECT_PLAN.md).

Không có chương `07-Mock` trong bộ tài liệu chính. Mock exporter chỉ là công cụ hỗ trợ phát triển khi chưa có dữ liệu từ hệ thống thật.

## Chạy mock exporter

Mock exporter cung cấp dữ liệu Prometheus local cho sáu KPI và một số signal hạ tầng.

```powershell
cd mock-exporter
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python mock_metrics.py
```

Kiểm tra:

```powershell
Invoke-RestMethod http://localhost:8000/health
Invoke-WebRequest http://localhost:8000/metrics
```

Exporter hỗ trợ ba kịch bản:

```powershell
Invoke-RestMethod -Method Post http://localhost:8000/scenario/normal
Invoke-RestMethod -Method Post http://localhost:8000/scenario/degraded
Invoke-RestMethod -Method Post http://localhost:8000/scenario/outage
```

Xem chi tiết tại [mock-exporter/README.md](mock-exporter/README.md).

## Prometheus scrape local

Khi Prometheus chạy trực tiếp trên máy:

```yaml
scrape_configs:
  - job_name: vid-mock
    scrape_interval: 5s
    static_configs:
      - targets:
          - localhost:8000
```

Nếu Prometheus chạy trong Docker Desktop, target thường là:

```yaml
targets:
  - host.docker.internal:8000
```

## Deployment lifecycle

Deployment lifecycle bảo đảm dashboard, rules và tài liệu được phát triển, kiểm tra và quản lý nhất quán bằng Git.

```text
Thiết kế
        |
        v
Phát triển
        |
        v
Validation
        |
        v
Review và Merge
        |
        v
Triển khai UAT
        |
        v
Xác nhận kết quả
        |
        +---- đạt ----> Bàn giao và cải tiến
        |
        +---- lỗi ----> Rollback và sửa đổi
```

Các giai đoạn chính:

- **Thiết kế:** chốt metric contract, KPI/SLI/SLO, dashboard và alert strategy.
- **Phát triển:** thay đổi dashboard, rules, tests và tài liệu trên feature branch.
- **Validation:** kiểm tra syntax, rules, tests và tính nhất quán của artifact.
- **Review và merge:** thay đổi qua Merge Request, CI và review.
- **Triển khai UAT:** đưa artifact đã duyệt vào môi trường tích hợp để xác nhận ở mức tổng quan; thao tác chi tiết theo quy trình nội bộ.
- **Bàn giao hoặc rollback:** bàn giao khi đạt yêu cầu, hoặc khôi phục phiên bản ổn định và sửa đổi qua Git.

Xem thêm [tổng quan triển khai](docs/09-Deployment.md) và [quy trình GitOps](docs/08-GitOps.md).

## Trạng thái hiện tại

| Hạng mục | Trạng thái |
|---|---|
| Tổng quan và kế hoạch dự án | Hoàn thành bản đầu |
| Tài liệu KPI/SLI/SLO | Có bản đề xuất, chờ owner xác nhận |
| Metric contract | Có bản đề xuất, chờ đối chiếu instrumentation thật |
| Prometheus scrape | Chưa cấu hình |
| Recording rules | Chưa triển khai |
| Alert rules | Chưa triển khai |
| Grafana dashboard JSON | Chưa triển khai |
| Runbook | Chưa triển khai |
| Triển khai môi trường tích hợp | Chưa thực hiện |

## Các bước tiếp theo

1. Xác định observability repository và convention hiện hành.
2. Lấy quyền read-only vào Prometheus/Grafana của môi trường tích hợp.
3. Kiểm kê metric thật và label cardinality.
4. Đối chiếu metric thật với sáu KPI.
5. Chốt KPI, SLI, SLO và alert threshold với owner.
6. Viết PromQL, recording rules và unit tests.
7. Tạo dashboard Grafana và alert rules.
8. Triển khai và xác nhận tổng quan tại UAT.


## Definition of Done

Dự án được coi là hoàn thành khi:

- Sáu KPI được owner phê duyệt.
- Metric contract được đối chiếu với dữ liệu thật.
- Recording/alert rules qua lint và unit test.
- Dashboard import được, không có panel/query error.
- Alert đã được xác nhận trong môi trường kiểm thử.
- Mỗi alert có owner và runbook.
- Không có PII, secret hoặc label cardinality nguy hiểm.
- Có xác nhận kết quả và phương án rollback.
