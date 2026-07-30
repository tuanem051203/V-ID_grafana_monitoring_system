# V-ID Metrics Simulator

Deployable FastAPI component that exposes deterministic V-ID metrics for
local/UAT observability testing.

Run from this directory:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
PYTHONPATH=src uvicorn vid_mock_metrics.main:app --host 0.0.0.0 --port 8000
```

Configuration is loaded from `config/scenarios.yaml`. Override it with
`VID_SCENARIOS_FILE`; set the initial profile with `VID_INITIAL_SCENARIO`.

This service owns metric generation only. Prometheus, dashboard, alert and
deployment configuration belong to their respective top-level domains.
