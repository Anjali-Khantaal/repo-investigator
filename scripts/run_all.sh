#!/usr/bin/env bash
set -euo pipefail

bash scripts/run_mlflow.sh &
MLFLOW_PID=$!

bash scripts/run_backend.sh &
BACKEND_PID=$!

bash scripts/run_frontend.sh &
FRONTEND_PID=$!

cleanup() {
  kill "$MLFLOW_PID" "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}

trap cleanup EXIT INT TERM
wait
