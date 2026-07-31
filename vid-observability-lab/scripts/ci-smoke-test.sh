#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
COMPOSE_FILE="$PROJECT_ROOT/deployments/local/docker-compose.yml"
CI_PROJECT_NAME="vid-ci-${GITHUB_RUN_ID:-local}-${GITHUB_RUN_ATTEMPT:-1}"

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
export VID_LOAD_PROFILE=${VID_LOAD_PROFILE:-development}

compose up --build --detach

wait_for_url "metrics simulator" "http://localhost:8000/health"
wait_for_url "Prometheus" "http://localhost:9090/-/ready"
wait_for_url "Alertmanager" "http://localhost:9093/-/ready"
wait_for_url "Grafana" "http://localhost:3000/api/health" 60

python3 - <<'PY'
import json
import time
import urllib.request


def get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=5) as response:
        return json.load(response)


metrics = urllib.request.urlopen("http://localhost:8000/metrics", timeout=5).read()
assert b"auth_requests_total" in metrics, "expected V-ID metrics were not exposed"

rules = get_json("http://localhost:9090/api/v1/rules")
assert rules["status"] == "success", rules
assert rules["data"]["groups"], "Prometheus loaded no rule groups"

deadline = time.time() + 30
while True:
    targets = get_json("http://localhost:9090/api/v1/targets")
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

grafana = get_json("http://localhost:3000/api/health")
assert grafana["database"] == "ok", grafana
PY

echo "Integration smoke test passed"

