# 09 — Tổng quan triển khai

## 1. Mục tiêu

Quy trình triển khai bảo đảm dashboard, recording rules, alert rules và tài liệu được kiểm tra, review và quản lý nhất quán bằng Git.

## 2. Vòng đời chung

```text
Thiết kế
   |
   v
Phát triển
   |
   v
Validation
   |
   v
Review và Merge
   |
   v
Triển khai UAT
   |
   v
Xác nhận kết quả
   |
   +---- đạt ----> Bàn giao và cải tiến
   |
   +---- lỗi ----> Rollback và sửa đổi
```

## 3. Các giai đoạn

### Thiết kế

Chốt metric contract, KPI/SLI/SLO, cấu trúc dashboard, alert strategy và owner.

### Phát triển

Dashboard, rules, tests và tài liệu được thay đổi trên feature branch. Không đưa credential, secret hoặc PII vào repository.

### Validation

Kiểm tra syntax, Prometheus rules, unit tests, dashboard và tính nhất quán với KPI đã định nghĩa.

### Review và merge

Merge Request ghi rõ phạm vi, kết quả kiểm tra, ảnh hưởng và phương án khôi phục. Thay đổi chỉ được merge khi qua review và CI.

### Triển khai UAT

Artifact đã được review được đưa vào UAT để xác nhận khả năng hoạt động với cấu hình và dữ liệu của môi trường tích hợp. Phần triển khai chi tiết tuân theo quy trình nội bộ của đơn vị vận hành.

### Xác nhận và bàn giao

Đội dự án xác nhận dashboard và rules hoạt động đúng mục tiêu, ghi nhận vấn đề còn lại, cập nhật tài liệu và bàn giao cho owner.

### Rollback

Khi có lỗi, khôi phục phiên bản ổn định trước đó và thực hiện bản sửa đổi thông qua feature branch/Merge Request mới.

## 4. Artifact

| Artifact | Yêu cầu chung |
|---|---|
| Dashboard JSON | Version control, UID ổn định, không chứa secret |
| Recording rules | Hợp lệ và có test |
| Alert rules | Có owner, mô tả và runbook |
| Documentation | Khớp với artifact và KPI |
| Configuration | Tách biệt khỏi credential |

## 5. Nguyên tắc

- Git là nguồn dữ liệu chuẩn cho artifact.
- Không sửa thủ công mà không đồng bộ lại repository.
- Cùng một thay đổi phải đi qua validation và review.
- Mock chỉ hỗ trợ phát triển; xác nhận cuối dùng dữ liệu phù hợp của môi trường.
- Mọi lỗi và điều chỉnh được xử lý bằng thay đổi có lịch sử.
