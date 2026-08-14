# 06 — Alerting và runbook

## Nguyên tắc

Page theo user impact hoặc burn rate, không page chỉ vì một pod/CPU cao. Alert phải
có owner, environment, service thực, dashboard và runbook. Threshold lab chưa được
dùng cho UAT/production trước khi có baseline và phê duyệt.

## Nhóm alert theo kiến trúc V-ID

- IdP authentication/challenge/login suy giảm.
- Hydra authorize/token hoặc `oauth2-token` front suy giảm.
- OTP route/provider submission/delivery receipt suy giảm theo country/channel.
- Redis/Postgres/Kafka dependency tác động tới IdP/session/challenge.
- `authz` enforce system error/latency; policy denial không mặc định là outage.
- Kong/critical endpoint availability.
- Telemetry target/rule/collector/Tempo health.

OTP triage phải phân biệt:

```text
IdP/Kong latency
vs Redis challenge persistence
vs Notification Center queue
vs GSM provider submission
vs carrier delivery receipt delay
```

## Severity

| Severity | Điều kiện | Route |
|---|---|---|
| critical | outage, mất receipt diện rộng, fast burn | on-call/paging |
| warning | suy giảm kéo dài, slow burn, backlog | team channel/ticket |
| info | deployment/synthetic scenario | annotation/event |

## Triage

1. Xác nhận environment, flow và issuer.
2. Xác định client/realm/country/provider bị ảnh hưởng bằng bounded labels.
3. Từ symptom dashboard tìm stage/service đầu tiên suy giảm.
4. Mở Tempo exemplar; kiểm tra change/deployment gần nhất.
5. Xác minh dependency/provider và delivery-report contract.
6. Mitigate/rollback theo quyền hạn; theo dõi recovery và ghi timeline.

Group theo alert/environment/cluster/service, inhibit warning khi critical cùng
scope, dùng traffic floor và `for` duration để giảm noise.
