#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
cd "$PROJECT_ROOT"

ENVIRONMENTS=$(python3 -c 'import json; print(" ".join(json.load(open("deployments/config.json"))["environments"]))')
for environment in $ENVIRONMENTS; do
  python3 scripts/render-config.py --environment "$environment" >/dev/null
done

PYTHONPATH=services/metrics-simulator/src \
  python3 -m compileall -q services/metrics-simulator/src
PYTHONPATH=services/metrics-simulator/src \
python3 -m unittest discover -s services/metrics-simulator/tests -v
python3 -m unittest discover -s tests/dashboard -v
for dashboard in observability/grafana/dashboards/*.json; do
  python3 -m json.tool "$dashboard" >/dev/null
done
for simulator_config in services/metrics-simulator/config/*.json; do
  python3 -m json.tool "$simulator_config" >/dev/null
done
for deployment_config in deployments/*.json; do
  python3 -m json.tool "$deployment_config" >/dev/null
done
promtool check rules observability/prometheus/rules/vid-kpi-rules.yml
promtool check rules observability/prometheus/rules/vid-cross-region-rules.yml
for environment in $ENVIRONMENTS; do
  promtool check config "generated/$environment/prometheus/prometheus.yml"
  promtool check rules "generated/$environment/prometheus/rules/vid-alert-rules.yml"
  (
    cd "generated/$environment/alertmanager"
    amtool check-config alertmanager.yml
  )
done
promtool test rules tests/prometheus/vid-kpi-rules.test.yml
promtool test rules tests/prometheus/vid-cross-region-rules.test.yml
GRAFANA_ADMIN_PASSWORD=validation-only \
VID_SMTP_APP_PASSWORD=validation-only \
  docker compose -f generated/local/docker-compose.yml config --quiet

echo "Validation passed"
