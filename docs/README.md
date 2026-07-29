# V-ID Observability Documentation

Bộ tài liệu thiết kế và vận hành hệ thống monitoring cho V-ID.

## Mục lục

1. [01 — Overview](01-Overview.md) — kiến trúc monitoring và phạm vi hệ thống.
2. [02 — KPI, SLI, SLO](02-KPI-SLI-SLO.md) — định nghĩa 6 KPI và mục tiêu dịch vụ.
3. [03 — Metrics](03-Metrics.md) — thiết kế metric phục vụ từng KPI.
4. [04 — Prometheus](04-Prometheus.md) — scrape, recording rules và alert rules.
5. [05 — Grafana](05-Grafana.md) — cấu trúc dashboard và visualization.
6. [06 — Alerting](06-Alerting.md) — alert strategy, routing và runbook.
7. [08 — GitOps](08-GitOps.md) — quản lý dashboard/rules bằng Git.
8. [09 — Deployment](09-Deployment.md) — tổng quan vòng đời triển khai.

Không có chương `07-Mock`. Dữ liệu giả lập chỉ là công cụ hỗ trợ phát triển, không phải một phần kiến trúc hoặc quy trình vận hành chính thức.

## Trạng thái tài liệu

Các tên metric trong tài liệu là **metric contract đề xuất**. Trước khi áp dụng cần đối chiếu với instrumentation thực tế, xác nhận SLO target với service owner và thay toàn bộ placeholder về URL, UID, owner và notification route.
