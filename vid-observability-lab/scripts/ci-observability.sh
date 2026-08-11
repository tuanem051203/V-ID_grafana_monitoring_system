#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
python3 "$PROJECT_ROOT/scripts/render-config.py" --environment local >/dev/null
PROMETHEUS_IMAGE=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["images_prometheus"])' "$PROJECT_ROOT/generated/local/resolved.json")
ALERTMANAGER_IMAGE=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["images_alertmanager"])' "$PROJECT_ROOT/generated/local/resolved.json")

docker run --rm \
  --entrypoint promtool \
  -v "$PROJECT_ROOT/generated/local/prometheus:/etc/prometheus:ro" \
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
  -v "$PROJECT_ROOT/generated/local/alertmanager:/etc/alertmanager:ro" \
  -w /etc/alertmanager \
  "$ALERTMANAGER_IMAGE" \
  check-config /etc/alertmanager/alertmanager.yml
