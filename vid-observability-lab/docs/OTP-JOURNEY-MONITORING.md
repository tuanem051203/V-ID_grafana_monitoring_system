# International OTP Journey Monitoring

## 1. Mục tiêu

Chức năng này mô phỏng và giám sát toàn bộ hành trình gửi SMS OTP quốc tế của
V-ID nhằm trả lời các câu hỏi:

- OTP journey có thành công không và mất tổng cộng bao lâu?
- Request bắt đầu chậm hoặc lỗi tại stage/service nào?
- Sự cố nằm trong Kong, Identity Provider, Redis, hàng đợi hay phía GSM/carrier?
- Chỉ một country/provider bị ảnh hưởng hay toàn bộ luồng dùng chung bị suy giảm?
- Một request được sample đã tiêu tốn thời gian như thế nào trên trace waterfall?

Đây là implementation cho môi trường demo. Metrics, traces, country distribution,
latency và failure đều là dữ liệu synthetic.

## 2. Cơ sở kiến trúc V-ID

Nguồn tham chiếu:

- `../../docs/v-id-intern-docs/docs/architecture/architecture.md`
- `../../docs/v-id-intern-docs/docs/architecture/components.md`
- `../../docs/v-id-intern-docs/docs/architecture/gateway-routing.md`

Theo tài liệu V-ID, `identity-provider` sở hữu OTP và dùng `RoutingSMSSender` để
chọn channel/provider. Số +84 tiếp tục qua Notification Center; destination được
allowlist có thể route qua GSM, còn WhatsApp là một channel/policy riêng.

Quốc gia của số điện thoại không chứng minh V-ID chạy compute hoặc có datacenter
tại quốc gia đó. Vì vậy implementation không dùng mô hình “VN datacenter →
destination-country datacenter” để kết luận bottleneck OTP. Boundary được mô phỏng
theo service/dependency của hành trình gửi OTP:

```text
Client/edge
  → Kong
  → identity-provider
  → Redis challenge persistence
  → OTP route selection
  → Notification Center queue
  → GSM/provider submission
  → carrier delivery receipt
```

Provider chấp nhận request không đồng nghĩa người dùng đã nhận SMS. Delivery
receipt được theo dõi như một boundary bất đồng bộ riêng.

## 3. Các stage đã triển khai

| Stage | Service target | Nội dung mô phỏng |
|---|---|---|
| `edge_to_kong` | `kong` | Thời gian từ edge/ingress tới Kong |
| `kong_to_idp` | `identity-provider` | Kong chuyển request tới IdP |
| `redis_challenge` | `redis` | IdP lưu OTP challenge |
| `route_selection` | `identity-provider` | Chọn route/channel/provider |
| `queue_wait` | `notification-center` | Message chờ consumer xử lý |
| `gsm_submit` | `gsm-gateway` | Gửi request và chờ provider chấp nhận |
| `carrier_delivery` | `sms-provider` | Chờ delivery receipt từ carrier/provider |

Simulator xử lý các stage tuần tự. Khi một stage thất bại:

1. Stage đó được ghi nhận với `result="failure"`.
2. `otp_journey_failures_total` ghi stage/service/reason terminal.
3. Các stage phía sau không được sinh.
4. Journey kết thúc với `result="failure"`.

Nhờ đó, việc không có `carrier_delivery` không tự động có nghĩa carrier lỗi; request
có thể đã dừng tại Redis, queue hoặc `gsm_submit`.

## 4. Metrics đã triển khai

### End-to-end journey

| Metric | Type | Ý nghĩa |
|---|---|---|
| `otp_journey_requests_total` | Counter | Tổng journey theo country/channel/provider/result |
| `otp_journey_duration_seconds` | Histogram | Tổng latency của các stage đã đi qua |
| `otp_journey_failures_total` | Counter | Terminal failure theo stage/service/reason |

### Per-stage và delivery

| Metric | Type | Ý nghĩa |
|---|---|---|
| `otp_stage_requests_total` | Counter | Request đến được từng stage và result |
| `otp_stage_duration_seconds` | Histogram | Latency tại từng stage/service |
| `otp_queue_wait_duration_seconds` | Histogram | Thời gian chờ Notification Center queue |
| `otp_delivery_reports_total` | Counter | Delivery receipt success/failure |
| `otp_delivery_duration_seconds` | Histogram | Thời gian provider submission → receipt |
| `otp_queue_size` | Gauge | Queue depth hiện tại |

Labels được giới hạn ở các giá trị bounded như `source_region`,
`destination_country`, `channel`, `provider`, `stage`, `service`, `result` và
`reason`. Không đưa phone number, OTP, user/session/challenge/request ID, token
hoặc `trace_id` vào Prometheus labels.

## 5. Cách simulator sinh một journey

Mỗi batch tạo một tỷ lệ international OTP từ authentication traffic, sau đó:

1. Chọn destination country theo traffic weight cấu hình.
2. Dùng channel `sms` và synthetic provider `gsm`.
3. Sinh latency log-normal riêng cho từng stage.
4. Áp dụng baseline failure rate hoặc degradation đang active.
5. Cộng stage duration thành end-to-end duration.
6. Dừng ngay tại terminal failure.
7. Ghi Prometheus counter/histogram.
8. Sample khoảng 10% journey để phát synthetic trace.

Country hiện được mô phỏng gồm `us`, `dk`, `id`, `ph`, `la`, `in`, `kz`, `ru`
và `nl`. Danh sách này phục vụ demo/filter, không phải production routing contract.

## 6. Distributed tracing đã triển khai

```text
metrics-simulator
  └─ OTLP/gRPC
      → OpenTelemetry Collector
      → Tempo
      → Grafana Explore / Traces Drilldown
```

Root span có tên `POST /v1/auth/challenge`; mỗi stage là một child span tuần tự.
Trace chỉ chứa bounded attributes:

```text
otp.destination_country
otp.channel
otp.provider
otp.stage
otp.result
service.target
simulation.synthetic
```

Histogram end-to-end đính kèm exemplar `trace_id`, cho phép từ panel Grafana mở
đúng waterfall trong Tempo. `trace_id` chỉ nằm trong exemplar, không trở thành
Prometheus series label.

Tempo chạy monolithic cho lab. Tempo 2.8 bật metrics-generator với processor
`local-blocks` để Grafana Traces Drilldown chạy được TraceQL metrics như `rate()`.

## 7. Recording rules và alerts

Các recorded series đã triển khai:

```text
vid:otp_journey_requests:rate5m
vid:otp_journey_success:ratio5m
vid:otp_journey_latency:p95_5m
vid:otp_stage_latency:p95_5m
vid:otp_stage_error:ratio5m
vid:otp_delivery_latency:p95_5m
```

Các alert chính:

- `VIDOTPJourneyLatencyHigh`: end-to-end p95 vượt ngưỡng demo.
- `VIDOTPStageDegraded`: stage latency hoặc error ratio tăng.
- `VIDOTPDeliveryReceiptMissing`: vẫn có journey nhưng không có delivery report.
- Alert queue backlog hiện có dùng `otp_queue_size`.

Threshold hiện chỉ phục vụ lab; không dùng làm SLO/alert production trước khi có
baseline và owner phê duyệt.

## 8. Dashboard đã triển khai

Dashboard: **V-ID SSO — OTP Journey**

URL local: `http://localhost:3000/d/sso-otp-journey`

Các panel gồm:

- OTP journeys/second.
- Journey success ratio.
- End-to-end journey p95.
- Delivery receipt p95.
- Stage latency p95 — bottleneck locator.
- Stage error ratio.
- Terminal failure theo stage/service/reason.
- Queue depth và queue-wait p95.
- Raw journey latency có trace exemplars.

Variables gồm `environment`, `cluster`, `destination_country`, `channel`,
`provider` và `stage`.

## 9. Khởi chạy local

```bash
cd vid-observability-lab
cp .env.example .env
```

Đặt tối thiểu trong `.env`:

```dotenv
GRAFANA_ADMIN_PASSWORD=admin
VID_SMTP_APP_PASSWORD=unused
```

Render và chạy stack:

```bash
python3 scripts/render-config.py --environment local
docker compose --env-file .env -f generated/local/docker-compose.yml up --build -d
```

Kiểm tra:

```bash
curl http://localhost:8000/health
curl http://localhost:3200/ready
docker compose --env-file .env -f generated/local/docker-compose.yml ps
```

Tempo không có web UI tại `http://localhost:3200/`; response 404 ở `/` là bình
thường. Trace được xem qua Grafana tại `http://localhost:3000`.

## 10. Tạo degradation scenario

Ví dụ làm chậm carrier delivery cho Indonesia trong 420 giây:

```bash
curl -X POST http://localhost:8000/api/simulation/warnings/otp-journey-degradation \
  -H 'content-type: application/json' \
  -d '{
    "duration_seconds": 420,
    "destination_region": "id",
    "hop": "carrier_delivery",
    "latency_multiplier": 5,
    "failure_rate": 0.15
  }'
```

`hop` có thể là bất kỳ stage nào trong bảng ở mục 3. Xóa scenario:

```bash
curl -X DELETE \
  http://localhost:8000/api/simulation/warnings/otp-journey-degradation
```

Tạo queue backlog riêng:

```bash
curl -X POST http://localhost:8000/api/simulation/warnings/otp-queue-backlog \
  -H 'content-type: application/json' \
  -d '{"duration_seconds":420,"queue_size":500}'
```

## 11. Quy trình phát hiện bottleneck

### Bước 1 — Xác nhận end-to-end symptom

Kiểm tra Journey success, Journey p95 và Delivery p95. Nếu chỉ Delivery p95 tăng,
synchronous API path có thể vẫn bình thường.

### Bước 2 — Thu hẹp phạm vi

Filter theo `destination_country`, `provider` và `channel`. Nếu mọi country cùng
chậm tại một internal stage, nghi ngờ shared V-ID component. Nếu chỉ một country
chậm tại provider/delivery, nghi ngờ route/carrier cụ thể.

### Bước 3 — Tìm stage đầu tiên lệch baseline

```promql
vid:otp_stage_latency:p95_5m{
  destination_country="id",
  provider="gsm"
}
```

Không chọn stage có duration tuyệt đối lớn nhất; so sánh mỗi stage với baseline
của chính nó. `carrier_delivery` tự nhiên dài hơn Redis.

### Bước 4 — Đối chiếu error, throughput và queue

```promql
vid:otp_stage_error:ratio5m{
  destination_country="id",
  provider="gsm"
}
```

```promql
sum by (stage) (
  rate(otp_stage_requests_total{
    destination_country="id",
    provider="gsm"
  }[5m])
)
```

Stage trước bình thường, stage hiện tại chậm/lỗi và traffic stage sau giảm là dấu
hiệu boundary hiện tại gây nghẽn. Với queue, cần thấy cả queue depth và queue-wait
tăng trước khi kết luận backlog.

### Bước 5 — Xác minh bằng Tempo waterfall

Trong dashboard, mở panel **Journey latency with trace exemplars**, nhấn exemplar
`trace_id` và mở bằng Tempo. Hoặc vào Grafana Explore → Tempo và query:

```traceql
{ resource.service.name = "vid-metrics-simulator" }
```

Đọc root duration, child span dài nhất, stage failure đầu tiên và khoảng thời gian
không được child span giải thích. Một trace chỉ là sample; cần đối chiếu nhiều trace
và metrics tổng hợp trước khi kết luận.

## 12. Mẫu kết luận

| Tín hiệu | Kết luận nghi ngờ |
|---|---|
| `redis_challenge` p95 tăng, trace dừng tại Redis | Redis/network/pool bottleneck |
| Queue depth và `queue_wait` cùng tăng | Notification Center consumer/backlog |
| `gsm_submit` chậm/lỗi, receipt giảm | Provider submission/API bottleneck |
| `gsm_submit` nhanh, `carrier_delivery` chậm | Provider/carrier delivery delay |
| Mọi country chậm tại `kong_to_idp` | Shared Kong/IdP boundary |
| Chỉ một country/provider chậm | Route/provider-specific degradation |

Chỉ kết luận khi có ít nhất hai tín hiệu đồng thuận, ví dụ stage p95 + trace span,
error ratio + failure reason, hoặc queue depth + queue wait.

## 13. Giới hạn và hướng production

Implementation hiện tại không phải distributed system thật: một simulator tạo
metrics và spans mang tên các service target khác nhau. Nó chứng minh dashboard,
PromQL, alerts, exemplars và trace workflow, không chứng minh production topology.

Khi tích hợp V-ID thật cần:

1. Instrument Kong và từng Go service bằng OpenTelemetry middleware.
2. Propagate W3C `traceparent` qua HTTP/gRPC.
3. Inject/extract trace context qua Kafka/message headers.
4. Instrument Redis/DB và outbound provider client.
5. Correlate provider callback bằng identifier đã privacy-review.
6. Tách synchronous submission trace khỏi asynchronous delivery bằng span link
   hoặc trace strategy được owner thống nhất.
7. Thay synthetic country/provider weights và thresholds bằng topology/baseline thật.
8. Xác nhận sampling, retention, access control và telemetry ownership.

Không đưa phone, OTP, token, cookie hoặc thông tin định danh vào metric labels,
span attributes hay logs chưa qua privacy/security review.
