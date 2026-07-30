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
VID_LOAD_PROFILE=development \
  PYTHONPATH=src \
  uvicorn vid_mock_metrics.main:app --host 0.0.0.0 --port 8000
```

`config/simulation.yaml` định nghĩa bốn profile:

| `VID_LOAD_PROFILE` | Peak TPS |
|---|---:|
| `development` | 20 |
| `uat` | 100 |
| `production` | 500 |
| `peak` | 2000 |

`VID_SIMULATION_DAY_SECONDS` mặc định là `86400`, tương ứng thời gian thực. Có
thể đặt `3600` để chạy trọn lịch 24 giờ trong một giờ demo. Random có seed ổn
định; đổi `VID_RANDOM_SEED` khi cần một lần chạy khác nhưng vẫn tái lập được.

API `/api/simulation` trả profile, thời gian mô phỏng, TPS hiện tại và event đang
hoạt động. `/metrics` chỉ chứa raw metrics và các gauge trạng thái simulator.

## Incident tự động

Mỗi ngày mô phỏng tự chạy Morning Login Peak, Database Slow, SMS Gateway
Failure, Redis Restart và Rolling Deployment. Effect chỉ tồn tại trong khoảng
thời gian cấu hình rồi tự phục hồi, không reset counter và không cần restart.
