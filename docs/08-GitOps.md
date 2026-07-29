# 08 — GitOps cho Dashboard và Rules

## 1. Mục tiêu

Dashboard, recording rules và alert rules phải được quản lý như code: có lịch sử, review, validation và triển khai lặp lại được.

## 2. Cấu trúc đề xuất

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
docs/
  ...
scripts/
  validate.ps1
```

Nếu observability repository có convention khác, ưu tiên convention hiện hành.

## 3. Workflow

```text
Feature branch
    |
    v
Edit dashboard/rules/docs
    |
    v
Local validation
    |
    v
Merge Request + Review
    |
    v
CI validation
    |
    v
Merge
    |
    v
UAT confirmation
```

## 4. Pull/Merge Request checklist

- Mục tiêu và phạm vi thay đổi.
- KPI/SLO liên quan.
- Screenshot hoặc dashboard evidence.
- Kết quả `promtool` và test.
- Query/cardinality impact.
- Security/PII review.
- Kế hoạch xác nhận UAT.
- Kế hoạch rollback.
- Owner và runbook.

## 5. CI gates

- YAML/JSON syntax.
- `promtool check rules`.
- `promtool test rules`.
- Grafana dashboard schema/lint nếu tooling hỗ trợ.
- Tìm secret.
- Kiểm tra placeholder bị cấm trong artifact triển khai.
- Kiểm tra file generated có đồng bộ với source.

## 6. Dashboard workflow

Một trong hai mô hình phải được chốt:

1. JSON trong Git là source of truth; Grafana được provision từ Git.
2. Dashboard được chỉnh trong môi trường tích hợp, export JSON chuẩn hóa rồi review trong Git.

Không chỉnh trực tiếp trên môi trường dùng chung mà không đồng bộ ngược về Git.

## 7. Versioning và rollback

- Commit nhỏ, có mục đích rõ.
- Dashboard UID ổn định.
- Rule name không đổi tùy tiện vì ảnh hưởng series/alert history.
- Rollback bằng revert commit hoặc deploy phiên bản artifact trước đó.
- Mọi hotfix trên môi trường dùng chung phải được backport vào Git.

## 8. Phân quyền

- Developer: tạo branch/MR.
- Reviewer/SRE: kiểm tra query, alert và vận hành.
- Owner: phê duyệt KPI/SLO.
- Deployment automation/service account: quyền tối thiểu cần thiết.
