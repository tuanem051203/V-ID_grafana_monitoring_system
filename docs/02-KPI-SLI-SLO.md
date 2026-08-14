# 02 — KPI, SLI và SLO cho V-ID

Các target trong lab là đề xuất, không phải cam kết production. Owner phải xác
nhận numerator, denominator, exclusion, traffic floor và window bằng dữ liệu thật.

| KPI/SLI | Boundary V-ID | Good event | Eligible event | Trạng thái |
|---|---|---|---|---|
| Authentication success | IdP challenge/login hoặc Hydra login completion | terminal success | terminal valid attempt | Proposed |
| Authentication latency | cùng boundary với flow được chọn | duration trong threshold | completed eligible attempt | Proposed |
| OTP provider submission | IdP/Notification Center/GSM client | provider accepts message | provider submission attempt | Proposed |
| OTP delivery | provider delivery receipt | receipt `delivered` | message accepted và có receipt contract | Proposed |
| OTP verification | IdP challenge verification | verified | terminal verify attempt | Product baseline; chưa alert SLO |
| Token issuance | issuer thực tế: Hydra hoặc IdP trong transition | token issued | protocol-valid terminal request | Proposed |
| Platform availability | critical Kong/service operations | không có system 5xx/timeout | valid critical request | Proposed |
| AuthZ decision service | `authz` enforce API | quyết định được trả đúng hạn | valid enforcement request | Proposed |

## Quy tắc phân loại

- Không trộn invalid credential, wrong/expired OTP hoặc policy denial với system
  availability nếu owner chưa phê duyệt.
- Retry của provider là delivery attempt, không phải unique user journey.
- `provider accepted` không đồng nghĩa SMS đã tới thiết bị; delivery receipt là
  boundary riêng.
- Token metric phải có `issuer` hoặc operation đủ rõ trong giai đoạn dual issuer.
- Browser flow và native transition flow không được cộng latency nếu boundary bắt
  đầu/kết thúc khác nhau.

## SLO ban đầu trong lab

- Authentication success: 99.9% / rolling 30d.
- Authentication dưới 500 ms: 95% / rolling 30d.
- OTP delivery: 95% / 24h và 30d.
- Token issuance: 99.9% / rolling 30d.
- Platform availability: 99.9% / rolling 30d.

Các số này chỉ dùng để kiểm thử recording/alert rules. International carrier
delivery cần SLO riêng theo country/provider/channel sau khi có baseline.

## Error budget

```text
allowed_bad_ratio = 1 - SLO
burn_rate = observed_bad_ratio / allowed_bad_ratio
```

Chỉ page bằng multi-window burn rate khi có đủ traffic. No-data phải được phân
biệt với 0% lỗi và với 100% thành công.
