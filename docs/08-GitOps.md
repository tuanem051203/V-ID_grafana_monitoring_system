# 08 — GitOps cho V-ID observability

`docs/v-id-intern-docs` là architecture input; source code, rules, dashboards và
deployment templates trong `vid-observability-lab` là executable artifacts. Một
thay đổi topology/flow phải cập nhật cả contract, simulator, query, test và docs.

## Source of truth

```text
docs/v-id-intern-docs/                  V-ID architecture snapshot
vid-observability-lab/services/         synthetic simulator
vid-observability-lab/observability/    dashboard/rules/Alertmanager
vid-observability-lab/deployments/      environment templates
vid-observability-lab/tests/            contract/rule tests
vid-observability-lab/docs/             operational docs
```

Không chỉnh trực tiếp generated config hoặc Grafana dùng chung mà không đồng bộ
về source. `generated/<environment>` được tạo lại bởi `render-config.py`.

## Review checklist

- Mapping tới component/flow nào trong `v-id-intern-docs`?
- Đây là current state, transition hay ADR target?
- Synthetic assumption đã được đánh dấu chưa?
- Metric labels có PII/high cardinality không?
- Numerator/denominator, issuer và delivery boundary có nhất quán không?
- Prometheus rules/dashboard/Compose/OTel config và tests đã đồng bộ chưa?
- Có UAT evidence, owner, runbook và rollback không?

## CI và rollback

CI kiểm tra Python, JSON/YAML, dashboard contract, `promtool`, Alertmanager config,
rendered Compose, dependency/container scan và smoke test. Giữ UID/rule name ổn
định. Rollback bằng revert hoặc artifact version trước; không sửa history hay xóa
thay đổi của người khác.
