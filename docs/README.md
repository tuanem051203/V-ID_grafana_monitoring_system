# Documentation map

Điểm vào duy nhất cho tài liệu repository, giúp phân biệt **V-ID đang là gì**,
**lab đã triển khai gì**, và **cần làm gì để vận hành**.

## Thứ tự ưu tiên nguồn

1. [`v-id-intern-docs`](v-id-intern-docs/README.md) — snapshot chuẩn về V-ID
   architecture, eKYC và AuthZ; không sửa để khớp giả định lab.
2. [`OBSERVABILITY.md`](OBSERVABILITY.md) — cách ánh xạ domain V-ID vào telemetry,
   KPI/SLI/SLO, dashboard, alert và deployment lifecycle.
3. [`vid-observability-lab/docs`](../vid-observability-lab/docs) — contract và
   runbook gắn trực tiếp với executable artifacts.
4. README cạnh component — hướng dẫn build/chạy/cấu hình component đó.

Nếu tài liệu mâu thuẫn: dùng `v-id-intern-docs` làm mặc định, sau đó xác nhận
living document và owner trước khi thay contract/code.

## Bản đồ câu hỏi

| Câu hỏi | Tài liệu |
|---|---|
| V-ID có capability nào? | [Products](v-id-intern-docs/docs/architecture/products.md), [feature status](v-id-intern-docs/docs/architecture/features.md) |
| Service/dependency thật tên gì? | [Components](v-id-intern-docs/docs/architecture/components.md) |
| AuthN/AuthZ/OAuth chạy thế nào? | [Architecture](v-id-intern-docs/docs/architecture/architecture.md), [AuthZ](v-id-intern-docs/docs/authz) |
| Hostname route tới đâu? | [Gateway routing](v-id-intern-docs/docs/architecture/gateway-routing.md) |
| Lab quan sát boundary nào? | [Observability handbook](OBSERVABILITY.md) |
| KPI tính và loại trừ ra sao? | [KPI contract](../vid-observability-lab/docs/KPI-CONTRACT.md) |
| Chạy/cấu hình/validate thế nào? | [Lab README](../vid-observability-lab/README.md) |
| OTP/cross-region có nghĩa gì? | [OTP journey](../vid-observability-lab/docs/OTP-JOURNEY-MONITORING.md), [cross-region](../vid-observability-lab/docs/CROSS-REGION-MONITORING.md) |
| Alert xảy ra thì làm gì? | [Runbook](../vid-observability-lab/docs/RUNBOOK.md) |
| Thư mục nào có ownership gì? | [Repository structure](../vid-observability-lab/docs/REPOSITORY-STRUCTURE.md) |

## Quy tắc duy trì

- Link tới `v-id-intern-docs` thay vì sao chép mô tả domain.
- Đánh dấu mọi synthetic assumption; không trình bày như production fact.
- Lấy số dashboard/rule/panel từ artifact, không từ báo cáo milestone.
- Đổi contract phải đồng bộ simulator, rules, dashboard, tests và runbook.
- Không lưu PII, secret, token, OTP hoặc endpoint chưa được duyệt.
- Lưu progress/prompt ở issue hoặc Merge Request, không coi là canonical docs.
