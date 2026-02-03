#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Running backend tests..."
cd "${ROOT_DIR}"
pytest -q

echo "Running frontend build..."
cd "${ROOT_DIR}/frontend"
npm run build
