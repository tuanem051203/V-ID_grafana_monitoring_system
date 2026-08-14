# 05 — Grafana dashboards

## Dashboard model

Dashboard đi từ user journey tới component thật:

1. Overview: authentication, OTP, token và platform symptoms.
2. Authentication: phân biệt native transition flow và browser Hydra flow khi có
   dữ liệu thật.
3. MFA & OTP: send, provider submission, delivery receipt và verification.
4. OTP Journey: Kong → IdP → Redis/routing → queue → GSM/carrier.
5. Token Lifecycle: có dimension issuer trong thời kỳ Hydra/IdP transition.
6. Authorization: `authz` enforcement và policy denial.
7. Platform/Reliability: service/dependency saturation, SLO và alerts.
8. Cross-region: chỉ là generic synthetic test dashboard, không phải sơ đồ mạng V-ID.

## Variables

Luôn có `environment`, `cluster`; thêm bounded `service`, `operation`, `issuer`,
`realm`, `channel`, `provider`, `destination_country`, `stage` khi metric hỗ trợ.
Không tạo variable từ phone, client ID không kiểm soát hoặc raw endpoint.

## Drill-down

Prometheus cho biết country/provider/stage bị suy giảm. Exemplar mở trace Tempo để
xem waterfall của request được sample. Production có thể nối span sang structured
logs bằng `trace_id` sau privacy review.

## Quy ước hiển thị

- Stat cho trạng thái hiện tại; time series cho rate/ratio/latency.
- Percent dùng 0–100%, duration dùng ms/s; no-data khác zero.
- Panel description ghi boundary, công thức và exclusion.
- UID/datasource UID ổn định; JSON không chứa credential hay URL cá nhân.
- Không mặc định mọi OTP quốc tế đi qua region/datacenter của quốc gia nhận.

## Acceptance

Dashboard import/provision không sửa tay, không query error, hoạt động ở 15m–30d,
filters không tạo query quá nặng, và tên service khớp workload V-ID được owner xác
nhận. Synthetic alias phải được đánh dấu rõ.
