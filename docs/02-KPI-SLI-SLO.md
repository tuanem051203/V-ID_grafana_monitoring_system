# 02 — KPI, SLI và SLO

## 1. Khái niệm

- **KPI**: chỉ số phản ánh sức khỏe hoặc kết quả nghiệp vụ.
- **SLI**: phép đo kỹ thuật dùng để đánh giá chất lượng dịch vụ.
- **SLO**: mục tiêu định lượng của SLI trong một cửa sổ thời gian.
- **Error budget**: phần lỗi được phép, bằng `1 - SLO`.

Target dưới đây là đề xuất khởi tạo. Service owner phải xác nhận trước khi áp dụng.

## 2. Danh mục 6 KPI

| ID | KPI | SLI | Target đề xuất | Window |
|---|---|---|---|---|
| KPI-01 | Authentication success rate | Good terminal auth / valid terminal auth | ≥99.9% | Rolling 30 ngày |
| KPI-02 | Authentication latency | Tỷ lệ auth request dưới ngưỡng latency | ≥95% dưới 500 ms | Rolling 30 ngày |
| KPI-03 | OTP delivery success rate | Delivered OTP / send attempts | ≥95% | 24 giờ và 7 ngày |
| KPI-04 | OTP verification success rate | Successful verification / valid verification attempts | Baseline rồi chốt target | 24 giờ và 30 ngày |
| KPI-05 | Token issuance success rate | Issued token / valid token requests | ≥99.9% | Rolling 30 ngày |
| KPI-06 | Platform availability | Non-5xx critical requests / critical requests | ≥99.9% | Rolling 30 ngày |

## 3. KPI-01 — Authentication success rate

**Mục đích:** đo khả năng hoàn tất đăng nhập của người dùng hợp lệ.

- Numerator: auth attempt có terminal result `success`.
- Denominator: terminal result `success|failure`.
- Loại trừ: health check, synthetic test đã được đánh dấu, request chưa terminal.
- Business rejection cần được thống nhất có thuộc mẫu số hay không.
- Dimensions: environment, realm, client và auth method nếu cardinality cho phép.

## 4. KPI-02 — Authentication latency

**Mục đích:** đo thời gian xử lý authentication ở góc nhìn service.

- SLI chính: tỷ lệ request có duration ≤500 ms.
- Chỉ số quan sát bổ trợ: p50, p95 và p99.
- Nguồn: histogram, không dùng gauge percentile để tạo aggregate toàn hệ thống.
- Dimensions: environment, service, operation.
- Không gắn raw URL hoặc user identifier.

## 5. KPI-03 — OTP delivery success rate

**Mục đích:** đo khả năng chuyển OTP thành công qua provider.

- Numerator: OTP có terminal result `delivered`.
- Denominator: OTP send attempt có terminal result `delivered|failed`.
- Dimensions: environment, channel, country code, provider.
- Retry phải được phân biệt giữa delivery attempt và user journey.
- Không dùng phone number làm label.

## 6. KPI-04 — OTP verification success rate

**Mục đích:** theo dõi khả năng xác minh OTP.

- Numerator: verification result `success`.
- Denominator: terminal verification attempts.
- Tách `expired`, `invalid`, `rate_limited` và `system_error`.
- Business/user error không nên tự động được xem là availability failure.
- Target chỉ chốt sau khi có baseline và phân loại failure rõ ràng.

## 7. KPI-05 — Token issuance success rate

**Mục đích:** đo độ tin cậy của bước phát hành OAuth2/OIDC token.

- Numerator: token issuance result `success`.
- Denominator: valid terminal token requests.
- Dimensions: environment, issuer, grant type và client class.
- Loại trừ request vi phạm protocol hoặc client credential không hợp lệ nếu owner phê duyệt.

## 8. KPI-06 — Platform availability

**Mục đích:** đo mức sẵn sàng của endpoint trọng yếu.

- Numerator: critical request không trả về 5xx.
- Denominator: tất cả critical request hợp lệ.
- Endpoint critical phải được quản lý bằng danh sách rõ ràng.
- 4xx không mặc định là lỗi availability, nhưng phải theo dõi riêng.

## 9. Error budget

Với SLO 99.9% trong 30 ngày:

```text
Allowed bad ratio = 1 - 0.999 = 0.001
Allowed bad time  = 30 ngày × 0.001 ≈ 43.2 phút
```

Burn rate:

```text
Burn rate = observed bad-event ratio / allowed bad-event ratio
```

Burn rate lớn hơn 1 nghĩa là error budget đang bị tiêu thụ nhanh hơn mức bền vững.

