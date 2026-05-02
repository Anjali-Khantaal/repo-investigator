#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ -x "${PROJECT_ROOT}/.venv/bin/python" ]]; then
  export PATH="${PROJECT_ROOT}/.venv/bin:${PATH}"
fi

cd "${PROJECT_ROOT}"
echo "Starting Streamlit UI on http://localhost:8501"
exec streamlit run frontend/streamlit_app.py --server.port 8501
