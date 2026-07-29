# V-ID Grafana Monitoring System

## 1. Mục tiêu tài liệu

Tài liệu này là bản mô tả và kế hoạch triển khai từ đầu đến cuối cho dự án **V-ID KPIs Grafana Dashboard + SLO Alerting**. Nội dung được chia thành các đầu việc nhỏ, có đầu vào, đầu ra và tiêu chí hoàn thành để có thể giao cho Codex thực hiện từng phần độc lập.

Nguồn bối cảnh ban đầu: `V-ID-Field-Guide.html`.

> Trạng thái hiện tại: repository mới chỉ có `README.md`; chưa có dashboard, rule Prometheus, tài liệu metric, cấu hình datasource hay môi trường kiểm thử.

## 2. Nguyên tắc thiết kế

- Dashboard KPI ưu tiên góc nhìn người dùng, không chỉ CPU/RAM.
- Mỗi KPI phải có owner, công thức, đơn vị, nguồn metric và ngưỡng.
- Không đưa email, số điện thoại, user ID, access token hoặc OTP vào label/log/dashboard.
- Label phải có cardinality hữu hạn; không dùng `user_id`, `request_id`, `phone_number`, raw URL hoặc token.
- Recording rule dùng cho query lặp lại, query phức tạp và alert.
- Alert phải có `severity`, `service`, `environment`, `team`, mô tả và link runbook.
- Tách dấu hiệu lỗi triệu chứng (symptom) khỏi nguyên nhân hạ tầng (cause).
- Môi trường kiểm thử dùng để kiểm chứng rule và alert.
- Mọi ngưỡng ban đầu phải được hiệu chỉnh bằng baseline thực tế.

## 3. Bộ KPI đề xuất

Field Guide nói có **6 KPI có thể tính từ metric Prometheus hiện có**, nhưng chưa cung cấp tên metric hoặc định nghĩa chính thức. Bảng dưới đây là bộ KPI đề xuất để bắt đầu discovery; chỉ được coi là chính thức sau khi owner xác nhận.

| ID | KPI đề xuất | Câu hỏi trả lời | Công thức logic | Đơn vị |
|---|---|---|---|---|
| KPI-01 | Authentication success rate | Bao nhiêu lượt đăng nhập hoàn tất thành công? | successful auth / total terminal auth attempts | % |
| KPI-02 | Authentication latency p95 | Người dùng phải chờ bao lâu để hoàn tất bước auth? | p95 histogram của auth request/flow | giây |
| KPI-03 | OTP delivery success rate | OTP có tới nhà cung cấp/người dùng thành công không? | delivered OTP / OTP send attempts | % |
| KPI-04 | OTP verification success rate | Người dùng nhập OTP có xác thực thành công không? | successful OTP verification / total terminal verification attempts | % |
| KPI-05 | Token issuance success rate | OAuth2/OIDC token có được phát hành ổn định không? | successful token issuance / total terminal issuance attempts | % |
| KPI-06 | Platform availability/error rate | Các endpoint trọng yếu có sẵn sàng không? | successful critical requests / total critical requests, hoặc 1 - 5xx ratio | % |

### KPI bổ trợ nên có

- Request throughput theo service/endpoint/client/realm.
- Error rate theo error class, không theo error message tự do.
- Latency p50/p90/p95/p99.
- Active incidents và mức tiêu thụ error budget.
- OTP delivery theo country/channel/provider nếu label an toàn và cardinality được kiểm soát.
- Dependency health: Hydra, database, Kafka, OTP provider.
- Saturation: CPU, memory, pod restarts, connection pool, queue/consumer lag.

### Các câu hỏi cần chốt cho từng KPI

1. Event nào được tính là một attempt?
2. Retry có tính là attempt mới không?
3. Trạng thái nào là terminal, success, business rejection và technical failure?
4. Bot, health check, test client và internal traffic có bị loại không?
5. Cửa sổ tính là 5 phút, 1 giờ, 24 giờ hay 30 ngày?
6. Chiều phân tích nào được phép: environment, service, realm, client, country, channel, provider?
7. Dữ liệu trễ hoặc thiếu được hiển thị thế nào?
8. Owner và ngưỡng cảnh báo là ai/quy định nào?

## 4. Mẫu đặc tả KPI bắt buộc

Mỗi KPI sau khi discovery phải có một bản ghi theo mẫu:

```yaml
id: KPI-01
name: Authentication success rate
owner: <team-or-person>
business_definition: <definition>
numerator: <successful-events>
denominator: <eligible-terminal-attempts>
exclusions:
  - <health-check-or-test-traffic>
dimensions:
  - environment
  - realm
  - client
source_metrics:
  - <real_prometheus_metric_name>
recording_rules:
  - <recording_rule_name>
unit: percent
windows:
  - 5m
  - 1h
  - 24h
target: <approved-target>
warning_threshold: <approved-threshold>
critical_threshold: <approved-threshold>
missing_data_behavior: <no_data|keep_last_state|alert>
runbook: <url-or-repo-path>
approved_by: <owner>
```

## 5. PromQL mẫu

Các tên metric dưới đây chỉ là placeholder, không được đưa thẳng vào rule:

```promql
# Tỷ lệ thành công
sum(rate(<counter_total>{status="success"}[5m]))
/
clamp_min(sum(rate(<counter_total>{status=~"success|failure"}[5m])), 1)

# Latency p95
histogram_quantile(
  0.95,
  sum by (le, environment) (
    rate(<duration_seconds_bucket>[5m])
  )
)

# Error rate 5xx
sum(rate(<http_requests_total>{code=~"5.."}[5m]))
/
clamp_min(sum(rate(<http_requests_total>[5m])), 1)
```

Khi triển khai thật phải:

- Dùng counter và histogram đúng semantic.
- Giữ cùng bộ filter ở tử số và mẫu số.
- Không trộn business rejection với lỗi hệ thống.
- Xử lý traffic thấp và mẫu số bằng 0.
- Kiểm tra counter reset.
- Không average các percentile đã được tính sẵn.

## 6. Cấu trúc dashboard đề xuất

### Row 1 — Executive health

- Sáu stat panel tương ứng 6 KPI.
- Trạng thái SLO và error budget còn lại.
- Số alert firing.
- Time range và timestamp dữ liệu gần nhất.

### Row 2 — Authentication

- Success rate theo thời gian.
- Auth attempts/giây.
- Latency p50/p95/p99.
- Error breakdown theo error class.

### Row 3 — OTP

- Send/delivery/verification success rate.
- OTP volume theo channel.
- Delivery theo country/provider nếu metric hỗ trợ.
- Top failure reason đã chuẩn hóa.

### Row 4 — OAuth2/OIDC token

- Token issuance success rate và volume.
- Latency p95/p99.
- Failure theo grant type/client/issuer nếu label an toàn.

### Row 5 — Service/dependency health

- 5xx rate và latency theo service.
- Pod availability/restarts.
- Database/Kafka/Hydra/OTP provider health.

### Row 6 — SLO and alerts

- SLO compliance 30 ngày.
- Error budget remaining.
- Burn rate nhanh/chậm.
- Alert firing/pending và link runbook.

### Dashboard variables

- `environment`
- `cluster`
- `service`
- `realm`
- `client` nếu cardinality và phân quyền cho phép
- `country`, `channel`, `provider` chỉ cho OTP analytics khi metric hỗ trợ

Mặc định không dùng biến chọn tất cả nếu nó tạo query quá nặng. Mỗi panel phải có title rõ, unit đúng, legend hữu ích và mô tả công thức.

## 7. SLI, SLO và alerting

Target chính thức phải do service owner phê duyệt. Có thể dùng ví dụ sau để thiết kế kỹ thuật:

| SLI | SLO minh họa | Cửa sổ |
|---|---|---|
| Auth availability | 99.9% auth request hợp lệ thành công | rolling 30 ngày |
| Auth latency | 95% request dưới ngưỡng đã chốt | rolling 30 ngày |
| Token issuance | 99.9% token request hợp lệ thành công | rolling 30 ngày |
| OTP delivery | ≥95% cho thị trường đủ điều kiện | 24 giờ/7 ngày |

Alert nên ưu tiên multi-window, multi-burn-rate:

- Fast burn: phát hiện outage/regression lớn, cửa sổ ngắn.
- Slow burn: phát hiện suy giảm kéo dài, cửa sổ dài.
- No data: chỉ cảnh báo khi phải có traffic/metric.
- Recording/Prometheus rule evaluation failure.
- Exporter/scrape target down.
- Dependency degradation khi ảnh hưởng user journey.

Mỗi alert phải có:

- Tên và biểu thức có thể kiểm thử.
- `for` duration để giảm nhiễu.
- Severity và route phù hợp.
- Summary mô tả tác động người dùng.
- Dashboard link và runbook link.
- Owner/escalation path.

## 8. Kế hoạch thực hiện từ đầu đến cuối

### Giai đoạn 0 — Khởi tạo và xin quyền truy cập

- [ ] T0.1 Xác định owner kỹ thuật, owner nghiệp vụ và người duyệt KPI/SLO.
- [ ] T0.2 Lấy quyền read Prometheus/Grafana cho môi trường kiểm thử.
- [ ] T0.3 Xác định observability repository, cấu trúc thư mục và quy trình MR.
- [ ] T0.4 Thu thập Grafana/Prometheus version, datasource UID và provisioning method.
- [ ] T0.5 Xác định quy trình triển khai artifact của tổ chức.
- [ ] T0.6 Ghi nhận kênh alert, routing và on-call owner.

**Hoàn thành khi:** có access matrix, owner list, repo/branch workflow và môi trường đích.

### Giai đoạn 1 — Discovery metric

- [ ] T1.1 Liệt kê toàn bộ target/service thuộc V-ID trong Prometheus.
- [ ] T1.2 Export metric names và metadata (`HELP`, `TYPE`, unit).
- [ ] T1.3 Tìm counter/histogram cho auth, OTP, token và HTTP.
- [ ] T1.4 Kiểm tra label, cardinality và dữ liệu nhạy cảm.
- [ ] T1.5 Kiểm tra dữ liệu có tồn tại trong môi trường kiểm thử và độ dài retention.
- [ ] T1.6 Đối chiếu 6 KPI trong wiki/roadmap với metric thật.
- [ ] T1.7 Lập metric gap analysis; tách gap có thể xử lý bằng query và gap cần code instrumentation.

**Đầu ra:** `docs/metric-inventory.md`, `docs/kpi-gap-analysis.md`.

**Hoàn thành khi:** mỗi KPI có ít nhất một nguồn metric khả dụng hoặc được đánh dấu blocked với owner/action rõ ràng.

### Giai đoạn 2 — Chốt KPI và SLO

- [ ] T2.1 Viết đặc tả cho từng KPI theo mẫu ở mục 4.
- [ ] T2.2 Xác định tử số, mẫu số, exclusion và dimensions.
- [ ] T2.3 Phân biệt lỗi kỹ thuật, lỗi nghiệp vụ và hành vi người dùng.
- [ ] T2.4 Phân tích baseline 7–30 ngày nếu retention cho phép.
- [ ] T2.5 Đề xuất target, warning, critical và no-data behavior.
- [ ] T2.6 Review với service owner/SRE/product owner.
- [ ] T2.7 Lưu lại quyết định và người phê duyệt.

**Đầu ra:** `docs/kpi-catalog.md`, `docs/slo-definition.md`.

**Hoàn thành khi:** cả 6 KPI được phê duyệt và không còn placeholder trong định nghĩa.

### Giai đoạn 3 — PromQL và recording rules

- [ ] T3.1 Viết query thô cho từng KPI trong Prometheus Explore.
- [ ] T3.2 Kiểm tra query với traffic bình thường, traffic thấp, no-data và lỗi spike.
- [ ] T3.3 Chuẩn hóa tên recording rule và label.
- [ ] T3.4 Tạo rule cho rate, ratio, latency quantile và SLI.
- [ ] T3.5 Chạy `promtool check rules`.
- [ ] T3.6 Viết unit test bằng `promtool test rules`.
- [ ] T3.7 Đánh giá hiệu năng query và cardinality.

**Đầu ra:** `prometheus/rules/vid-kpi-recording-rules.yaml`, `prometheus/tests/vid-kpi-rules.test.yaml`.

**Hoàn thành khi:** lint/test pass, query trả đúng dữ liệu và được reviewer xác nhận.

### Giai đoạn 4 — Grafana dashboard

- [ ] T4.1 Chốt datasource UID, folder, tags và dashboard UID ổn định.
- [ ] T4.2 Tạo variables và giá trị mặc định.
- [ ] T4.3 Tạo 6 KPI stat panels.
- [ ] T4.4 Tạo các time-series và breakdown panels.
- [ ] T4.5 Thêm SLO/error-budget/alert panels.
- [ ] T4.6 Cấu hình thresholds, units, legend, tooltip và panel description.
- [ ] T4.7 Thêm annotations cho deploy/incident nếu nguồn dữ liệu hỗ trợ.
- [ ] T4.8 Export dashboard JSON sạch, không chứa credential hoặc datasource ID cục bộ.
- [ ] T4.9 Kiểm tra dashboard ở time range 15m, 6h, 24h, 7d và 30d.

**Đầu ra:** `grafana/dashboards/vid-kpis.json`.

**Hoàn thành khi:** dashboard import được vào instance sạch, không có panel error và hiển thị đầy đủ sáu KPI đã được phê duyệt.

### Giai đoạn 5 — Alert rules và runbook

- [ ] T5.1 Tạo alert cho SLO burn rate và lỗi nghiêm trọng.
- [ ] T5.2 Thêm alert cho no-data/rule evaluation failure khi phù hợp.
- [ ] T5.3 Cấu hình labels, annotations, dashboard URL và runbook URL.
- [ ] T5.4 Viết runbook cho từng nhóm alert.
- [ ] T5.5 Test trạng thái inactive, pending, firing và resolved.
- [ ] T5.6 Xác minh notification route trong môi trường kiểm thử.
- [ ] T5.7 Thu thập feedback và hiệu chỉnh ngưỡng để giảm alert noise.

**Đầu ra:** `prometheus/rules/vid-kpi-alerts.yaml`, `docs/runbooks/`.

**Hoàn thành khi:** alert test pass, notification đến đúng nơi và người trực có thể xử lý bằng runbook.

### Giai đoạn 6 — Review, UAT và bàn giao

- [ ] T6.1 Chạy toàn bộ validation/lint/test.
- [ ] T6.2 Review security, PII và label cardinality.
- [ ] T6.3 Review dashboard với V-ID team, SRE và product owner.
- [ ] T6.4 Tạo MR vào observability repository.
- [ ] T6.5 Đưa artifact vào UAT theo quy trình nội bộ và xác nhận ở mức tổng quan.
- [ ] T6.6 Ghi nhận kết quả, phương án rollback và các vấn đề còn lại.
- [ ] T6.7 Bàn giao tài liệu vận hành và backlog tiếp theo.

**Hoàn thành khi:** MR được duyệt, kết quả UAT được xác nhận, dashboard/rules hoạt động và có rollback/runbook.

## 9. Chia task để giao cho Codex

Mỗi task dưới đây nên được giao trong một prompt/phiên làm việc riêng. Không yêu cầu Codex đoán metric hoặc credential.

| Task | Phụ thuộc | Nội dung giao | Kết quả mong đợi |
|---|---|---|---|
| C01 | Không | Khảo sát repo và tạo cấu trúc dự án | Folder skeleton, README, validation commands |
| C02 | Access Prometheus | Phân tích metric export/snapshot | Metric inventory và candidate mapping |
| C03 | C02 + wiki KPI | Viết KPI catalog và gap analysis | 6 đặc tả KPI, danh sách gap |
| C04 | C03 approved | Viết PromQL exploration queries | Query file có chú thích và kết quả kiểm chứng |
| C05 | C04 | Tạo recording rules | YAML hợp lệ, tên/label chuẩn |
| C06 | C05 | Viết promtool unit tests | Test cases normal/error/no-data |
| C07 | C05 | Tạo Grafana dashboard JSON | Dashboard import được |
| C08 | SLO approved + C05 | Tạo SLO/burn-rate alerts | Alert YAML và test |
| C09 | C08 | Viết runbooks | Runbook theo alert group |
| C10 | C06–C09 | Tạo validation script/CI | Một lệnh chạy toàn bộ checks |
| C11 | C10 | Xác nhận tổng quan UAT | Báo cáo kết quả và vấn đề còn lại |
| C12 | C11 | Chuẩn bị MR và handover | MR description, rollback, backlog |

### Prompt mẫu cho Codex

```text
Thực hiện task Cxx trong PROJECT_PLAN.md.

Đầu vào:
- Repository: <path>
- Metric/query snapshot: <path hoặc endpoint đã được cấp quyền>
- KPI đã phê duyệt: <path>
- Quy ước observability repo: <path>

Yêu cầu:
1. Chỉ sửa các file thuộc phạm vi task.
2. Không tự đoán tên metric, datasource UID, SLO target hoặc alert route.
3. Nếu thiếu dữ liệu, ghi rõ blocker và tạo placeholder có nhãn TODO; không tạo cấu hình giả như đã chạy được.
4. Chạy validation phù hợp và báo kết quả.
5. Cuối cùng liệt kê file đã thay đổi, quyết định kỹ thuật, test đã chạy và việc còn thiếu.

Acceptance criteria:
- <copy tiêu chí hoàn thành tương ứng từ PROJECT_PLAN.md>
```

## 10. Cấu trúc repository mục tiêu

```text
.
├── README.md
├── PROJECT_PLAN.md
├── docs/
│   ├── architecture.md
│   ├── access-and-owners.md
│   ├── metric-inventory.md
│   ├── kpi-catalog.md
│   ├── kpi-gap-analysis.md
│   ├── slo-definition.md
│   ├── uat-result.md
│   └── runbooks/
├── grafana/
│   ├── dashboards/
│   │   └── vid-kpis.json
│   └── provisioning/
├── prometheus/
│   ├── rules/
│   │   ├── vid-kpi-recording-rules.yaml
│   │   └── vid-kpi-alerts.yaml
│   └── tests/
│       └── vid-kpi-rules.test.yaml
├── scripts/
│   └── validate.ps1
└── .github/
    └── workflows/
        └── validate-observability.yml
```

Cấu trúc thực tế phải theo observability repository hiện hành nếu khác với đề xuất này.

## 11. Definition of Done toàn dự án

Dự án chỉ hoàn thành khi:

- [ ] Sáu KPI có định nghĩa và owner phê duyệt.
- [ ] Không còn placeholder metric/UID/threshold trong artifact triển khai.
- [ ] Recording rules và alert rules qua lint/unit test.
- [ ] Dashboard JSON import được và không có query/panel error.
- [ ] Dashboard được xác nhận tại UAT bằng dữ liệu phù hợp.
- [ ] Alert firing/resolved đã được kiểm thử có kiểm soát.
- [ ] Không lộ PII, secret, token hoặc label cardinality nguy hiểm.
- [ ] Mỗi alert có runbook và owner.
- [ ] Có MR review, xác nhận kết quả và rollback procedure.
- [ ] README giải thích vòng đời validate, triển khai và cập nhật dashboard/rules.

## 12. Rủi ro và cách xử lý

| Rủi ro | Ảnh hưởng | Cách xử lý |
|---|---|---|
| Metric không đủ để tính 6 KPI | Không thể hoàn thiện dashboard chính xác | Gap analysis, tạo ticket instrumentation, gán owner |
| Định nghĩa success/failure không thống nhất | KPI sai hoặc gây hiểu nhầm | KPI contract và approval trước khi code |
| Label cardinality cao | Prometheus/Grafana chậm, tăng chi phí | Audit label, aggregate trong recording rules |
| Traffic thấp ở môi trường kiểm thử | Ratio/alert nhiễu | Minimum traffic guard, test bằng fixture |
| Alert threshold đoán mò | Alert fatigue hoặc bỏ sót sự cố | Baseline 7–30 ngày và tune tại UAT |
| Dashboard phụ thuộc UID cục bộ | Import sang UAT thất bại | Stable dashboard UID và datasource variable/UID chuẩn |
| Dữ liệu auth chứa PII | Rủi ro bảo mật | Chỉ dùng label đã chuẩn hóa, review security |
| Query nặng trên range dài | Dashboard timeout | Recording rules, query inspection, giới hạn dimensions |

## 13. Việc nên làm ngay tiếp theo

1. Xin link/wiki chứa định nghĩa chính thức của 6 KPI.
2. Xác định observability repository thực tế và convention hiện có.
3. Lấy quyền read-only vào Prometheus/Grafana của môi trường kiểm thử.
4. Export metric metadata và một snapshot label an toàn.
5. Bắt đầu task **C02 — metric inventory**, sau đó mới chốt KPI/PromQL.
