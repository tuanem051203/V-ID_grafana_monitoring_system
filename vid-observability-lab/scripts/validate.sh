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
for dashboard in observability/grafana/dashboards/*.json; do
  python3 -m json.tool "$dashboard" >/dev/null
done
promtool check config observability/prometheus/prometheus.yml
promtool check rules observability/prometheus/rules/vid-kpi-rules.yml
promtool check rules observability/prometheus/rules/vid-alert-rules.yml
promtool test rules tests/prometheus/vid-kpi-rules.test.yml
for alertmanager_config in observability/alertmanager/alertmanager.*.yml; do
  alertmanager_config_name=$(basename "$alertmanager_config")
  (cd observability/alertmanager && amtool check-config "$alertmanager_config_name")
done
VID_SMTP_APP_PASSWORD=validation-only \
  docker compose -f deployments/local/docker-compose.yml config --quiet

echo "Validation passed"
