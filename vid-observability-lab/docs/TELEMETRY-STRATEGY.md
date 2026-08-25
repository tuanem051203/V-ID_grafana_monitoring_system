# V-ID Telemetry Strategy

## 1. Mục tiêu và phạm vi

Tài liệu này là policy kỹ thuật cho môi trường demo/local và baseline UAT của
V-ID Observability Lab. Nguồn cấu hình thực thi duy nhất là
`deployments/config.json`; tài liệu giải thích quyết định, không lặp lại một bộ
giá trị độc lập.

Baseline này chưa phải phê duyệt production. Trước production, service owner và
SRE phải xác nhận SLO, traffic baseline, dung lượng lưu trữ và on-call action.

## 2. Retention

| Signal | Baseline | Nơi thực thi | Lý do |
|---|---:|---|---|
| Metrics | 15 ngày | Prometheus `storage.tsdb.retention.time` | Đủ xem xu hướng demo/UAT ngắn hạn |
| Traces | 24 giờ | Tempo `compactor.compaction.block_retention` | Local lưu 100% nên giữ ngắn để giới hạn disk |
| Logs | 24 giờ | Loki `limits_config.retention_period` | Đồng bộ cửa sổ điều tra với traces |

Persistent volumes giữ dữ liệu qua container restart nhưng không thay thế
backup. Production phải dùng object storage, capacity plan và backup/DR riêng.

## 3. Sampling

| Environment | SDK sampler | OTP journey ratio | Mục đích |
|---|---|---:|---|
| local | `always_on` | 100% | Demo, kiểm chứng end-to-end và log/trace correlation |
| UAT | `parentbased_traceidratio` | 10% | Baseline với chi phí thấp hơn |
| production baseline | `parentbased_traceidratio` | 10% | Placeholder, cần capacity test và phê duyệt |

Collector không có sampling processor: quyết định sampling hiện nằm tại SDK.
W3C `traceparent,baggage` bảo toàn quyết định của upstream. Production nên cân
nhắc tail sampling để luôn giữ error/slow traces trước khi thay baseline 10%.

## 4. Alert thresholds

Các giá trị dưới đây lấy từ `defaults.telemetry.alerts`:

| Tín hiệu | Điều kiện | Pending | Severity/ý nghĩa |
|---|---|---|---|
| Metrics target | `up == 0` | 2m | Critical: mất telemetry source |
| Eligible traffic | không có traffic | 10m | Warning: traffic/instrumentation bất thường |
| SLO fast burn | burn rate > 14.4 trên 5m và 1h | 2m | Critical/page |
| SLO slow burn | burn rate > 6 trên 1h và 6h | 15m | Warning/ticket |
| OTP provider | status down | 2m | Warning |
| OTP queue | size > 100 | 5m | Warning |
| OTP journey | p95 > 8s | 5m | Warning |
| OTP stage | error > 5% hoặc p95 > 5s | 5m | Warning |
| Delivery receipt | không có receipt khi vẫn có traffic | 10m | Critical |
| Cross-region | success < 95% hoặc p95 > 1s | 5m | Critical/warning |
| Cross-region hop | error > 5% hoặc p95 > 750ms | 5m | Warning |

Threshold demo dùng để chứng minh workflow phát hiện và điều tra, không tự động
trở thành production SLO. Mỗi lần đổi threshold phải sửa `config.json`, render
lại cấu hình và chạy rule tests/smoke test.

## 5. Cardinality và dữ liệu nhạy cảm

- Prometheus labels chỉ dùng dimension hữu hạn; không dùng trace/request/user ID.
- Loki chỉ index `environment` và `service_name`.
- `trace_id`, `span_id`, `journey_id` là structured metadata để correlation.
- Không ghi số điện thoại, OTP code, token, password, Authorization header hoặc
  nội dung SMS vào metrics, logs hay trace attributes.

## 6. Quy trình thay đổi

1. Owner đề xuất SLI/SLO hoặc retention/sampling mới kèm traffic và capacity.
2. SRE cập nhật `deployments/config.json` và lý do trong tài liệu này.
3. Render cả local, UAT, production; không sửa trực tiếp `generated/`.
4. Chạy unit tests, Prometheus rule tests và integration smoke test.
5. Theo dõi ingest rate, disk growth, dropped spans/logs và alert noise sau rollout.
