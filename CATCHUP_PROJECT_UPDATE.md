# Cập nhật dự án V-ID Grafana Monitoring System

## 1. Mục tiêu dự án

Xây dựng hệ thống observability cho nền tảng V-ID SSO nhằm theo dõi trải nghiệm đăng nhập, OTP, phát hành token, phân quyền và sức khỏe nền tảng. Stack chính gồm **Prometheus, Grafana và Alertmanager**.

Hệ thống hướng tới việc giúp đội vận hành trả lời nhanh các câu hỏi:

- Người dùng có đăng nhập, nhận/xác minh OTP và lấy token thành công không?
- Latency và availability có đạt mục tiêu không?
- Sự cố đến từ service, dependency, provider hay hạ tầng nào?
- SLO và error budget đang ở trạng thái nào?

## 2. Các nội dung đã thực hiện

### Thiết kế monitoring

- Xây dựng kiến trúc và luồng monitoring từ metrics đến dashboard/cảnh báo.
- Đề xuất bộ **6 KPI chính**: authentication success, authentication latency, OTP delivery, OTP verification, token issuance và platform availability.
- Xây dựng metric contract, label policy và nguyên tắc kiểm soát cardinality/PII.
- Viết tài liệu KPI/SLI/SLO, deployment, GitOps và runbook xử lý sự cố.

### Metrics Simulator

- Xây dựng service FastAPI sinh mock metrics khi metrics thật chưa sẵn sàng.
- Mô phỏng các nhóm authentication, OTP, token, authorization, HTTP, infrastructure, database, provider và queue.
- Hỗ trợ nhiều traffic profile, latency giả lập và các incident tự kích hoạt/phục hồi.
- Có health endpoint, metrics endpoint và API xem trạng thái simulation.

### Prometheus và SLO

- Cấu hình Prometheus scrape Metrics Simulator.
- Xây dựng **51 recording rules** cho 6 KPI trên các cửa sổ `5m`, `1h`, `6h`, `24h` và `30d`.
- Tính error budget remaining và burn rate cho các KPI đã có SLO đề xuất.
- Có unit test cho Prometheus rules.

### Grafana

- Xây dựng và provision tự động **7 dashboard, tổng cộng 65 panel**:
  1. Tổng quan
  2. Đăng nhập & Xác thực
  3. MFA & OTP
  4. Token Lifecycle
  5. Phân quyền & Truy cập
  6. Nền tảng & Phụ thuộc
  7. SLO & Sự cố
- Dashboard hỗ trợ filter theo environment/cluster, time range và liên kết điều hướng giữa các màn hình.

### Alerting

- Xây dựng **11 alert rules** cho telemetry health, no traffic, SLO burn rate, suy giảm KPI, OTP provider và queue backlog.
- Bổ sung metadata phục vụ vận hành như severity, team, service, dashboard và runbook.
- Tách cấu hình Alertmanager cho local, UAT và production.
- Xây dựng email notification template; secret SMTP được tách khỏi source code.

#### Flow warning alert qua email

```text
Metrics Simulator / V-ID service
             ↓ /metrics
         Prometheus
             ↓ đánh giá alert rule mỗi 30 giây
   Điều kiện warning giữ đủ thời gian `for`
             ↓
         Alertmanager
             ↓ group theo alertname + environment + cluster + service
             ↓ chờ group_wait, route theo severity
         SMTP server
             ↓
      Email tới nhóm V-ID SRE
             ↓ khi metric phục hồi
       Email trạng thái RESOLVED
```

Các warning hiện có gồm:

- Không có eligible traffic trong 10 phút.
- SLO slow burn vượt `6x` trên cả cửa sổ `1h` và `6h`, duy trì 15 phút.
- OTP provider down trong 2 phút.
- OTP queue lớn hơn 100 message trong 5 phút.

Đối với production, warning được gửi tới receiver `production-warning-email`, dự kiến đến nhóm V-ID SRE. Alertmanager gom các cảnh báo cùng ngữ cảnh, chờ 30 giây trước lần gửi đầu, gom cập nhật trong khoảng 5 phút và nhắc lại sau 4 giờ nếu cảnh báo chưa được xử lý. Email có cả HTML/plain text, trạng thái, severity, environment, service, mô tả, link dashboard và runbook. Khi phục hồi, `send_resolved: true` gửi thêm email `RESOLVED`.

Alert `critical` được route riêng tới cả SRE và on-call, nhắc lại mỗi 1 giờ. Nếu warning và critical cùng environment/cluster/service, critical sẽ **inhibit warning** để tránh gửi trùng và giảm alert noise. Local hiện đã có cấu hình Gmail phục vụ kiểm thử; địa chỉ SMTP/receiver của UAT và production vẫn là placeholder, cần thay bằng thông tin chính thức và inject mật khẩu từ secret manager trước khi triển khai.

### GitOps và Configuration as Code

- Các cấu hình observability được quản lý trong Git thay vì chỉnh tay trên server: Prometheus scrape/rules, alert rules, Alertmanager routing theo môi trường, Grafana provisioning và Docker Compose đều được khai báo bằng **YAML**.
- Dashboard Grafana được lưu dưới dạng **JSON**, email notification được lưu thành template; tất cả cùng được version control, review và rollback theo commit.
- Git là source of truth: thay đổi được thực hiện trên feature branch, validate tại local, tạo Pull Request, chạy CI, review rồi mới merge và triển khai UAT.
- CI kiểm tra YAML/JSON, Prometheus rules, Alertmanager config, dashboard contract, Python service, dependency/container security và smoke test toàn stack.
- Dashboard dùng UID và datasource UID ổn định; rule name được giữ ổn định để không làm mất lịch sử series/alert.
- Khi có lỗi có thể rollback bằng revert commit hoặc triển khai lại phiên bản artifact trước đó. Mọi hotfix trên môi trường dùng chung phải được đồng bộ ngược về Git.

```text
Thay đổi file YAML/JSON/template
             ↓
        Feature branch
             ↓
       Validate tại local
             ↓
     Pull Request + review
             ↓
      CI quality gates
             ↓
        Merge vào main
             ↓
         Deploy UAT
             ↓
 Smoke test + lưu evidence
       ↙ đạt       ↘ lỗi
  Promote          Revert commit
```

### Chất lượng và CI

- Docker Compose để dựng toàn bộ stack local/UAT.
- GitHub Actions gồm lint/type check/unit test, dashboard contract test, Prometheus/Alertmanager validation, dependency audit, container build, Trivy scan và full-stack smoke test.
- Có script validation để chạy các quality gate tương ứng tại local trước khi review.

## 3. Trạng thái hiện tại

Baseline **local/UAT đã hoàn thiện các thành phần cốt lõi** và có thể dùng để demo luồng end-to-end:

`Metrics Simulator → Prometheus → Recording/Alert Rules → Grafana/Alertmanager`

Đây chưa phải production deployment. Dữ liệu hiện tại là dữ liệu mô phỏng và không được dùng để tự phê duyệt SLO hoặc capacity production.

## 4. Các nội dung cần thống nhất tiếp

- Xác nhận owner, numerator/denominator, exclusions, target và window cho từng KPI.
- Làm rõ OTP verification là product conversion KPI hay service SLI.
- Đối chiếu metric contract với instrumentation và dữ liệu thật của V-ID.
- Chốt critical endpoint, minimum traffic threshold và policy alert.
- Nhận thông tin UAT: service discovery, Grafana/Prometheus, SMTP/on-call route và secret manager.
- Thay các placeholder dashboard/runbook URL và thông tin notification trước khi release.
- Xác định phương án triển khai thật (Helm/Kustomize), HA, retention, storage, backup, SSO/RBAC/TLS.

## 5. Đề xuất bước tiếp theo

1. Review và chốt KPI/SLI/SLO cùng service owner/SRE.
2. Kết nối metrics thật tại UAT và so sánh với simulator contract.
3. Điều chỉnh PromQL, dashboard và alert threshold theo baseline thực tế.
4. Diễn tập các kịch bản normal, degradation, no-data, low traffic và recovery.
5. Hoàn thiện notification route/runbook, lưu evidence UAT và thống nhất tiêu chí promote production.

## 6. Nội dung có thể demo trong buổi catch-up

- Luồng khởi chạy full stack bằng Docker Compose.
- Dashboard tổng quan và drill-down theo authentication/OTP/token/platform.
- Cách incident mô phỏng làm thay đổi KPI, SLO burn rate và alert.
- Luồng warning/critical từ Prometheus sang Alertmanager, phân route và gửi email firing/resolved.
- Cách thay đổi cấu hình bằng YAML/JSON theo flow GitOps, các quality gate trong CI và phương án rollback.
- Phạm vi còn cần phối hợp để đưa lên UAT/production.

## 7. Các câu hỏi xin định hướng từ leader

- Phạm vi mong muốn của giai đoạn tiếp theo là hoàn thiện UAT hay chuẩn bị production?
- Ai là owner phê duyệt từng KPI/SLO và alert policy?
- Nguồn metrics thật và quyền truy cập môi trường UAT sẽ được cung cấp theo quy trình nào?
- Kênh nhận cảnh báo chính thức và yêu cầu escalation là gì?
- Có tiêu chuẩn nội bộ nào về deployment, security, dashboard hoặc observability cần áp dụng thêm không?
