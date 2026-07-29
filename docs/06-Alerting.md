# 06 — Alerting Strategy và Runbook

## 1. Mục tiêu

Alert phải phát hiện tác động thật, có người chịu trách nhiệm và dẫn tới hành động cụ thể. Dashboard dùng để quan sát; alert chỉ dùng cho tình huống cần can thiệp.

## 2. Cấp độ

| Severity | Ý nghĩa | Route |
|---|---|---|
| critical | Outage hoặc error budget burn rất nhanh | Paging/on-call |
| warning | Suy giảm kéo dài cần xử lý trong giờ làm việc | Team channel/ticket |
| info | Tín hiệu vận hành, không cần phản ứng ngay | Dashboard/event |

## 3. Nhóm alert

### User journey

- Authentication success rate thấp.
- Token issuance success rate thấp.
- Platform availability thấp.
- OTP delivery suy giảm theo country/provider.
- Authentication latency vượt SLO.

### SLO

- Fast burn: tác động lớn, phản ứng nhanh.
- Slow burn: suy giảm kéo dài.
- Error budget sắp cạn.

### Monitoring health

- Prometheus target down.
- Rule evaluation failure.
- Metric no-data khi có traffic kỳ vọng.
- Alertmanager notification failure.

### Dependency/resource

Chỉ page khi có quan hệ rõ với user impact. CPU/memory cao đơn thuần thường là warning hoặc context cho symptom alert.

## 4. Chống alert noise

- Dùng `for` duration.
- Yêu cầu minimum traffic trước khi đánh giá ratio.
- Group theo service/environment.
- Inhibit warning khi critical cùng nguyên nhân đang firing.
- Không alert theo từng pod nếu service-level symptom đã đủ.
- Tune ngưỡng bằng baseline của dữ liệu thực tế.

## 5. Alert annotation chuẩn

```yaml
labels:
  severity: critical
  service: identity-provider
  environment: uat
  team: vid
annotations:
  summary: <what is broken>
  description: <user impact, value, threshold, duration>
  dashboard_url: <stable dashboard link>
  runbook_url: <stable runbook link>
```

## 6. Mẫu runbook

Mỗi runbook gồm:

1. Alert name và mục đích.
2. User impact.
3. Điều kiện firing và query.
4. Owner/escalation.
5. Dashboard/log/tracing links.
6. Các bước xác minh.
7. Các nguyên nhân thường gặp.
8. Mitigation an toàn.
9. Điều kiện escalate/rollback.
10. Cách xác nhận recovery.
11. Hành động sau incident.

## 7. Quy trình triage chung

1. Xác nhận environment và thời điểm bắt đầu.
2. Kiểm tra KPI user journey và phạm vi ảnh hưởng.
3. Xác định service/client/realm/country bị ảnh hưởng.
4. Đối chiếu deployment hoặc configuration change gần nhất.
5. Kiểm tra dependency và resource saturation.
6. Thực hiện mitigation/rollback theo quyền hạn.
7. Theo dõi KPI hồi phục và alert resolved.
8. Ghi timeline, nguyên nhân và follow-up.

## 8. Kiểm thử alert

- Test rule bằng fixture.
- Xác nhận alert trong môi trường kiểm thử phù hợp.
- Xác minh pending → firing → resolved.
- Xác minh route, group và inhibition.
- Xác minh link dashboard/runbook.
