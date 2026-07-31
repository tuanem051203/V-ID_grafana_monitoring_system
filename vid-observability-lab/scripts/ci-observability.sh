#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
PROMETHEUS_IMAGE=${PROMETHEUS_IMAGE:-prom/prometheus:v3.5.0}
ALERTMANAGER_IMAGE=${ALERTMANAGER_IMAGE:-prom/alertmanager:v0.28.1}

docker run --rm \
  --entrypoint promtool \
  -v "$PROJECT_ROOT/observability/prometheus:/etc/prometheus:ro" \
  "$PROMETHEUS_IMAGE" \
  check config /etc/prometheus/prometheus.yml

docker run --rm \
  --entrypoint promtool \
  -v "$PROJECT_ROOT:/workspace:ro" \
  -w /workspace \
  "$PROMETHEUS_IMAGE" \
  test rules tests/prometheus/vid-kpi-rules.test.yml

docker run --rm \
  --entrypoint amtool \
  -v "$PROJECT_ROOT/observability/alertmanager:/etc/alertmanager:ro" \
  "$ALERTMANAGER_IMAGE" \
  check-config /etc/alertmanager/alertmanager.yml

