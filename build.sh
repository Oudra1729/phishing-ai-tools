#!/usr/bin/env bash
# Production build: Python deps + Vite React bundle (required for SPA / animations at /).
set -euo pipefail
cd "$(dirname "$0")"

pip install -r requirements.txt

if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
  echo "ERROR: Node.js 20+ and npm are required to build frontend/dist."
  echo "Install Node or deploy with Docker (see Dockerfile)."
  exit 1
fi

cd frontend
npm ci
npm run build

if [[ ! -f dist/index.html ]]; then
  echo "ERROR: frontend/dist/index.html was not created."
  exit 1
fi

echo "OK: frontend/dist ready — Flask will serve the React UI at /"
