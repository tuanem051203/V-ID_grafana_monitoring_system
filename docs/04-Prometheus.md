# 04 — Prometheus

## 1. Scrape configuration

Ví dụ minh họa:

```yaml
scrape_configs:
  - job_name: vid-identity-provider
    scrape_interval: 15s
    scrape_timeout: 10s
    metrics_path: /metrics
    static_configs:
      - targets:
          - identity-provider.example.internal:8080
        labels:
          environment: test
          service: identity-provider
```

Trong Kubernetes nên dùng `ServiceMonitor`/`PodMonitor` theo convention hiện có. Không hard-code credential trong repository.

## 2. Recording rules

Quy ước tên:

```text
<namespace>:<metric_expression>:<aggregation_or_window>
```

Ví dụ:

```yaml
groups:
  - name: vid-kpi-recording
    interval: 30s
    rules:
      - record: vid:auth_success:rate5m
        expr: |
          sum by (environment) (
            rate(auth_success_total[5m])
          )

      - record: vid:auth_attempts:rate5m
        expr: |
          sum by (environment) (
            rate(auth_requests_total[5m])
          )

      - record: vid:auth_success_ratio:rate5m
        expr: |
          vid:auth_success:rate5m
          /
          clamp_min(vid:auth_attempts:rate5m, 1)

      - record: vid:auth_latency_seconds:p95_5m
        expr: |
          histogram_quantile(
            0.95,
            sum by (environment, le) (
              rate(auth_request_duration_seconds_bucket[5m])
            )
          )
```

Tương tự cần tạo recorded ratio cho OTP delivery, OTP verification, token issuance và availability.

## 3. Alert rules

Ví dụ symptom alert:

```yaml
groups:
  - name: vid-kpi-alerts
    rules:
      - alert: VIDAuthenticationSuccessRateLow
        expr: vid:auth_success_ratio:rate5m < 0.99
        for: 10m
        labels:
          severity: warning
          service: identity-provider
          team: vid
        annotations:
          summary: V-ID authentication success rate is low
          description: Authentication success rate has been below 99% for 10 minutes.
          runbook_url: https://REPLACE-WITH-RUNBOOK
```

Ngưỡng ví dụ không được áp dụng trước khi owner phê duyệt.

## 4. SLO burn-rate rule

Với SLO 99.9%:

```promql
(
  1 - vid:auth_success_ratio:rate5m
)
/
(1 - 0.999)
```

Khi SLO được phê duyệt, nên dùng multi-window, multi-burn-rate. Ví dụ fast burn chỉ firing khi cả cửa sổ ngắn và dài đều vượt ngưỡng để giảm nhiễu.

## 5. Validation

```powershell
promtool check rules prometheus/rules/vid-kpi-recording-rules.yaml
promtool check rules prometheus/rules/vid-kpi-alerts.yaml
promtool test rules prometheus/tests/vid-kpi-rules.test.yaml
```

Test case tối thiểu:

- Traffic bình thường.
- Success rate giảm.
- Latency spike.
- Counter reset.
- Mẫu số bằng 0.
- No-data.
- Alert pending, firing và resolved.

## 6. Vận hành Prometheus

- Theo dõi `up`, scrape duration và scrape sample count.
- Alert khi rule evaluation fail.
- Kiểm tra query performance trước khi merge.
- Dùng recording rule cho query phức tạp/lặp lại.
- Retention phải hỗ trợ cửa sổ SLO.
- Giữ label set nhất quán giữa tử số và mẫu số.
