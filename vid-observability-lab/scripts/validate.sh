#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
cd "$PROJECT_ROOT"

PYTHONPATH=services/metrics-simulator/src \
  python3 -m compileall -q services/metrics-simulator/src
PYTHONPATH=services/metrics-simulator/src \
  python3 -m unittest discover -s services/metrics-simulator/tests -v
python3 -m json.tool \
  observability/grafana/dashboards/vid-kpis.json >/dev/null
python3 -m json.tool \
  observability/grafana/dashboards/vid-slo-operations.json >/dev/null
python3 -m json.tool \
  observability/grafana/dashboards/vid-identity-access.json >/dev/null
python3 -m json.tool \
  observability/grafana/dashboards/vid-application-performance.json >/dev/null
python3 -m json.tool \
  observability/grafana/dashboards/vid-infrastructure-database.json >/dev/null
promtool check config observability/prometheus/prometheus.yml
promtool check rules observability/prometheus/rules/vid-kpi-rules.yml
promtool check rules observability/prometheus/rules/vid-alert-rules.yml
promtool test rules tests/prometheus/vid-kpi-rules.test.yml
amtool check-config observability/alertmanager/alertmanager.yml
docker compose -f deployments/local/docker-compose.yml config --quiet

echo "Validation passed"
