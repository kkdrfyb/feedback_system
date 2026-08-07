#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> Running backend migrations"
cd "${ROOT_DIR}/backend"
if [ -f "feedback.db" ]; then
  NEED_STAMP="$(python - <<'PY' | tr -d '\r\n[:space:]'
import os, sqlite3
db = "feedback.db"
if not os.path.exists(db):
    print("0")
    raise SystemExit(0)
conn = sqlite3.connect(db)
try:
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'")
    has_alembic_table = cur.fetchone() is not None
    has_alembic_row = False
    if has_alembic_table:
        try:
            cur.execute("SELECT version_num FROM alembic_version LIMIT 1")
            has_alembic_row = cur.fetchone() is not None
        except sqlite3.Error:
            has_alembic_row = False
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    has_users = cur.fetchone() is not None
    print("1" if (has_users and not has_alembic_row) else "0")
finally:
    conn.close()
PY
)"
  if [ "${NEED_STAMP}" = "1" ]; then
    echo "Detected legacy DB without alembic_version; stamping head..."
    alembic -c alembic.ini stamp head
  fi
fi
alembic -c alembic.ini upgrade head

echo "==> Running legacy data health check"
cd "${ROOT_DIR}"
python scripts/check_legacy_data_health.py --strict

echo "==> Running backend tests"
pytest -q

echo "==> Running frontend build"
cd "${ROOT_DIR}/frontend"
npm ci
npm run build
