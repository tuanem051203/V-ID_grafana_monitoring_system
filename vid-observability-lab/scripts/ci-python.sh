#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
SERVICE_ROOT="$PROJECT_ROOT/services/metrics-simulator"

cd "$SERVICE_ROOT"

python3 -m ruff check src tests
python3 -m ruff format --check src tests
python3 -m pyright
python3 -m compileall -q src
PYTHONPATH=src python3 -m unittest discover -s tests -v

