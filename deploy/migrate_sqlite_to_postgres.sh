#!/usr/bin/env bash
# ==============================================================================
# PC SHOP — SAFE SQLITE TO POSTGRESQL DATA MIGRATION SCRIPT
# Preserves existing SQLite data (users, categories, products, discounts,
# reviews, orders) when transitioning a local SQLite database to PostgreSQL.
# ==============================================================================

set -euo pipefail

APP_DIR="${APP_DIR:-/var/www/shop_pc}"
SQLITE_FILE="${1:-${APP_DIR}/db.sqlite3}"
FIXTURE_FILE="/tmp/shop_pc_sqlite_export.json"

if [ ! -f "${SQLITE_FILE}" ]; then
    echo "No SQLite database found at ${SQLITE_FILE}; skipping SQLite data import."
    exit 0
fi

cd "${APP_DIR}"
echo "==> Exporting existing data from SQLite (${SQLITE_FILE})..."
DB_ENGINE=sqlite3 "${APP_DIR}/venv/bin/python" manage.py dumpdata \
    --natural-foreign --natural-primary \
    --exclude contenttypes --exclude auth.Permission --exclude admin.logentry --exclude sessions.session \
    --indent 2 --output "${FIXTURE_FILE}"

echo "==> Running PostgreSQL migrations..."
DB_ENGINE=postgresql "${APP_DIR}/venv/bin/python" manage.py migrate --noinput

echo "==> Loading exported data into PostgreSQL..."
DB_ENGINE=postgresql "${APP_DIR}/venv/bin/python" manage.py loaddata "${FIXTURE_FILE}"
rm -f "${FIXTURE_FILE}"
echo "==> SQLite to PostgreSQL data migration completed successfully."

