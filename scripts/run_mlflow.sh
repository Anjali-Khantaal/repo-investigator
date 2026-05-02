#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ -x "${PROJECT_ROOT}/.venv/bin/python" ]]; then
  export PATH="${PROJECT_ROOT}/.venv/bin:${PATH}"
fi

cd "${PROJECT_ROOT}"
if [[ -f ".env" ]]; then
  set -a
  source ".env"
  set +a
fi

MLFLOW_PORT="${MLFLOW_PORT:-5000}"
if [[ "${MLFLOW_TRACKING_URI:-}" =~ :([0-9]+)$ ]]; then
  MLFLOW_PORT="${BASH_REMATCH[1]}"
fi

echo "Starting MLflow on http://localhost:${MLFLOW_PORT}"
mkdir -p .mlflow
exec mlflow server \
  --host 0.0.0.0 \
  --port "${MLFLOW_PORT}" \
  --backend-store-uri sqlite:///./.mlflow/mlflow.db \
  --default-artifact-root ./mlruns
