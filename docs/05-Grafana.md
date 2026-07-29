# 05 — Grafana Dashboard

## 1. Mục tiêu dashboard

Dashboard “V-ID KPIs” phải cho biết sức khỏe user journey trong vòng 30–60 giây, sau đó cho phép drill-down theo service và nguyên nhân.

## 2. Cấu trúc dashboard

### Row 1 — KPI overview

Sáu stat panel:

1. Authentication success rate.
2. Authentication latency p95.
3. OTP delivery success rate.
4. OTP verification success rate.
5. Token issuance success rate.
6. Platform availability.

Mỗi stat có:

- Giá trị hiện tại.
- Sparkline.
- Threshold đã phê duyệt.
- Unit đúng.
- Link tới panel chi tiết.

### Row 2 — Authentication

- Attempts/giây.
- Success/failure theo thời gian.
- p50/p95/p99 latency.
- Failure reason và auth method breakdown.

### Row 3 — OTP

- Delivery và verification rate.
- Volume theo SMS/WhatsApp.
- Breakdown theo country/provider.
- Failure reason đã chuẩn hóa.

### Row 4 — Token và platform

- Token issuance rate/latency.
- HTTP throughput và 4xx/5xx.
- Availability theo service/operation.
- Dependency health.

### Row 5 — SLO

- 30-day SLO compliance.
- Error budget remaining.
- Fast/slow burn rate.
- Alert state và incident/deployment annotation.

## 3. Variables

| Variable | Mặc định | Ghi chú |
|---|---|---|
| `environment` | Môi trường đang quan sát | Bắt buộc |
| `service` | identity core | Multi-select có kiểm soát |
| `realm` | All | Chỉ khi cardinality an toàn |
| `client` | All hoặc client class | Tránh danh sách quá lớn |
| `country` | All | Chỉ cho OTP |
| `channel` | All | SMS/WhatsApp |

## 4. Visualization convention

- Stat: KPI hiện tại.
- Time series: trend, rate, ratio, latency.
- Bar chart: bounded category comparison.
- Table: alert, error reason, dependency state.
- Không dùng pie chart cho time series hoặc category quá nhiều.
- Ratio hiển thị percent 0–100%; duration hiển thị seconds/milliseconds.
- Success dùng xanh, warning vàng, critical đỏ; không chỉ dựa vào màu để truyền đạt trạng thái.

## 5. Query convention

- Ưu tiên recorded series.
- Query phải filter theo `$environment`.
- Legend ngắn, ổn định và có ý nghĩa.
- Không dùng range quá ngắn so với scrape interval.
- Panel description phải ghi công thức và exclusion.

## 6. Dashboard metadata

- UID ổn định: đề xuất `vid-kpis`.
- Title: `V-ID KPIs`.
- Tags: `vid`, `identity`, `slo`, `managed-by-git`.
- Folder theo convention của tổ chức.
- Dashboard JSON không chứa credential hoặc URL cá nhân.

## 7. Acceptance criteria

- Import được vào Grafana của môi trường kiểm thử mà không sửa tay.
- Không có datasource/panel/query error.
- Variables hoạt động và không tạo query quá nặng.
- Kiểm tra time range 15m, 6h, 24h, 7d và 30d.
- No-data được phân biệt với giá trị 0.
- Sáu KPI khớp với định nghĩa trong `02-KPI-SLI-SLO.md`.
