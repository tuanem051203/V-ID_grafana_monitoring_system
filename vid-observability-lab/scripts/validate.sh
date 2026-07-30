#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
cd "$PROJECT_ROOT"

PYTHONPATH=services/metrics-simulator/src \
  python3 -m compileall -q services/metrics-simulator/src
PYTHONPATH=services/metrics-simulator/src \
  python3 -m unittest discover -s services/metrics-simulator/tests -v
python3 -m unittest discover -s tests/dashboard -v
python3 -m json.tool \
  observability/grafana/dashboards/sso-overview.json >/dev/null
python3 -m json.tool \
  observability/grafana/dashboards/sso-authentication.json >/dev/null
python3 -m json.tool \
  observability/grafana/dashboards/sso-mfa-otp.json >/dev/null
python3 -m json.tool \
  observability/grafana/dashboards/sso-token-lifecycle.json >/dev/null
python3 -m json.tool \
  observability/grafana/dashboards/sso-authorization.json >/dev/null
python3 -m json.tool \
  observability/grafana/dashboards/sso-platform.json >/dev/null
python3 -m json.tool \
  observability/grafana/dashboards/sso-reliability.json >/dev/null
promtool check config observability/prometheus/prometheus.yml
promtool check rules observability/prometheus/rules/vid-kpi-rules.yml
promtool check rules observability/prometheus/rules/vid-alert-rules.yml
promtool test rules tests/prometheus/vid-kpi-rules.test.yml
amtool check-config observability/alertmanager/alertmanager.yml
docker compose -f deployments/local/docker-compose.yml config --quiet

echo "Validation passed"
