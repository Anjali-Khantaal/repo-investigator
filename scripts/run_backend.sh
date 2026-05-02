#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ -x "${PROJECT_ROOT}/.venv/bin/python" ]]; then
  # Prefer the repo-local environment so users can run the script directly.
  export PATH="${PROJECT_ROOT}/.venv/bin:${PATH}"
fi

cd "${PROJECT_ROOT}"
echo "Starting backend on http://localhost:8001"
echo "Open API docs at http://localhost:8001/docs"
exec uvicorn backend.app.main:app --host 0.0.0.0 --port 8001 --reload
