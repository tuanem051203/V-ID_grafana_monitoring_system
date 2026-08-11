#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
python3 "$PROJECT_ROOT/scripts/render-config.py" --environment local >/dev/null
COMPOSE_FILE="$PROJECT_ROOT/generated/local/docker-compose.yml"
RESOLVED_CONFIG="$PROJECT_ROOT/generated/local/resolved.json"
CI_PROJECT_NAME="vid-ci-${GITHUB_RUN_ID:-local}-${GITHUB_RUN_ATTEMPT:-1}"

config_value() {
  python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))[sys.argv[2]])' \
    "$RESOLVED_CONFIG" "$1"
}

METRICS_URL=$(config_value public_urls_metrics_simulator)
PROMETHEUS_URL=$(config_value public_urls_prometheus)
ALERTMANAGER_URL=$(config_value public_urls_alertmanager)
GRAFANA_URL=$(config_value public_urls_grafana)

compose() {
  docker compose -p "$CI_PROJECT_NAME" -f "$COMPOSE_FILE" "$@"
}

cleanup() {
  compose down --volumes --remove-orphans
}
trap cleanup EXIT

wait_for_url() {
  local name=$1
  local url=$2
  local attempts=${3:-40}

  for ((attempt = 1; attempt <= attempts; attempt++)); do
    if curl --fail --silent --show-error "$url" >/dev/null 2>&1; then
      echo "$name is ready"
      return 0
    fi
    sleep 3
  done

  echo "$name did not become ready: $url" >&2
  compose ps >&2
  compose logs --no-color >&2
  return 1
}

export GRAFANA_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD:-ci-only-password}
compose up --build --detach

wait_for_url "metrics simulator" "$METRICS_URL/health"
wait_for_url "Prometheus" "$PROMETHEUS_URL/-/ready"
wait_for_url "Alertmanager" "$ALERTMANAGER_URL/-/ready"
wait_for_url "Grafana" "$GRAFANA_URL/api/health" 60

METRICS_URL="$METRICS_URL" PROMETHEUS_URL="$PROMETHEUS_URL" GRAFANA_URL="$GRAFANA_URL" \
python3 - <<'PY'
import json
import os
import time
import urllib.request


def get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=5) as response:
        return json.load(response)


metrics_url = os.environ["METRICS_URL"]
prometheus_url = os.environ["PROMETHEUS_URL"]
grafana_url = os.environ["GRAFANA_URL"]

metrics = urllib.request.urlopen(f"{metrics_url}/metrics", timeout=5).read()
assert b"auth_requests_total" in metrics, "expected V-ID metrics were not exposed"

rules = get_json(f"{prometheus_url}/api/v1/rules")
assert rules["status"] == "success", rules
assert rules["data"]["groups"], "Prometheus loaded no rule groups"

deadline = time.time() + 30
while True:
    targets = get_json(f"{prometheus_url}/api/v1/targets")
    active = targets["data"]["activeTargets"]
    simulator = [
        target
        for target in active
        if target["labels"].get("job") == "vid-metrics-simulator"
    ]
    if simulator and simulator[0]["health"] == "up":
        break
    if time.time() >= deadline:
        raise AssertionError(f"metrics simulator target is not healthy: {simulator}")
    time.sleep(2)

grafana = get_json(f"{grafana_url}/api/health")
assert grafana["database"] == "ok", grafana
PY

echo "Integration smoke test passed"
