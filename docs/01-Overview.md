# 01 — Tổng quan kiến trúc monitoring

## Mục tiêu

Xây dựng nền tảng observability đầu tiên cho V-ID, giúp đội ngũ vận hành có thể theo dõi sức khỏe của hệ thống thông qua Platform KPIs, đồng thời chuẩn hóa quy trình triển khai (deployment lifecycle) của các monitoring artifacts từ phát triển đến UAT.

## Kiến trúc monitoring

```text
V-ID Services / Dependencies
        |
        |  /metrics
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
  +--> Service Detail
  +--> SLO / Error Budget
```

## Luồng dữ liệu

1. Service xuất metric theo Prometheus exposition format.
2. Prometheus scrape endpoint theo chu kỳ.
3. Recording rules tính trước rate, ratio, percentile và SLI.
4. Grafana đọc raw metrics và recorded series.
5. Alert rules đánh giá symptom và SLO burn rate.
6. Alertmanager group, route, inhibit và gửi notification.
7. Người trực dùng dashboard và runbook để triage.

## Môi trường

| Môi trường | Mục đích | Alert |
|---|---|---|
| Local/Dev | Phát triển query và dashboard | Không paging |
| UAT | Xác nhận dashboard, rules và tài liệu trong môi trường tích hợp | Kênh kiểm thử |

