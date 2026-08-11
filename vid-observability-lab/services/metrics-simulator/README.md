# V-ID Production-like Metrics Simulator

FastAPI service phát raw Prometheus metrics mô phỏng Identity Platform quy mô
doanh nghiệp. KPI không được export trực tiếp; Prometheus recording rules tính
KPI từ counter và histogram thô.

## Kiến trúc

- `config.py`: load và kiểm tra profile, baseline, traffic curve và event.
- `traffic.py`: nội suy cosine để traffic thay đổi mượt theo giờ.
- `events.py`: kích hoạt và tự kết thúc incident theo thời gian mô phỏng.
- `random_utils.py`: Gaussian noise có seed và log-normal latency.
- `generator.py`: chuyển traffic và event effects thành raw metrics.
- `metrics.py`: metric contract có cardinality hữu hạn.

## Chạy local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
APP_ENV=local \
CONFIG_FILE=config/runtime.json \
LOG_LEVEL=INFO \
PYTHONPATH=src \
uvicorn vid_mock_metrics.main:app --host 0.0.0.0 --port 8000
```

`config/runtime.json` là nguồn cấu hình có cấu trúc và định nghĩa bốn môi trường:

| `APP_ENV` | Load profile | Peak TPS | Simulation day |
|---|---|---:|---:|
| `local` | `development` | 20 | 86400 giây |
| `uat` | `uat` | 100 | 86400 giây |
| `production` | `production` | 500 | 86400 giây |
| `peak` | `peak` | 2000 | 3600 giây |

Env chỉ dùng để bootstrap: `APP_ENV` chọn môi trường, `CONFIG_FILE` trỏ tới JSON
được mount và `LOG_LEVEL` điều khiển log. Profile, thời gian mô phỏng, random
seed, traffic, baseline và incident đều được quản lý trong JSON. Schema tại
`config/runtime.schema.json` hỗ trợ editor và CI phát hiện cấu hình sai.

API `/api/simulation` trả profile, thời gian mô phỏng, TPS hiện tại và event đang
hoạt động. `/metrics` chỉ chứa raw metrics và các gauge trạng thái simulator.

## Test warning email theo yêu cầu

Bật kịch bản OTP queue backlog trong 7 phút:

```bash
curl -X POST http://localhost:8000/api/simulation/warnings/otp-queue-backlog \
  -H 'Content-Type: application/json' \
  -d '{"duration_seconds":420,"queue_size":150}'
```

Simulator giữ `otp_queue_size` lớn hơn 100. Sau 5 phút, Prometheus chuyển
`VIDOTPQueueBacklog` sang firing; Alertmanager gửi email sau `group_wait`. Kịch
bản tự hết hạn để kiểm tra email resolved. Thời lượng tối thiểu là 310 giây để
đảm bảo alert vượt qua `for: 5m`.

Kiểm tra hoặc dừng kịch bản sớm:

```bash
curl http://localhost:8000/api/simulation
curl -X DELETE http://localhost:8000/api/simulation/warnings/otp-queue-backlog
```

API điều khiển mô phỏng chỉ dành cho local/UAT và không được public ra Internet.

## Incident tự động

Mỗi ngày mô phỏng tự chạy Morning Login Peak, Database Slow, SMS Gateway
Failure, Redis Restart và Rolling Deployment. Effect chỉ tồn tại trong khoảng
thời gian cấu hình rồi tự phục hồi, không reset counter và không cần restart.
