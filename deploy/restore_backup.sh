#!/usr/bin/env bash
# ==============================================================================
# PC SHOP — BACKUP RESTORATION & VERIFICATION SCRIPT
# Usage:
#   1. Test restore into a temporary verification database:
#      sudo bash deploy/restore_backup.sh --verify /var/backups/shop_pc/daily/db_shop_pc_prod_YYYYMMDD_HHMMSS.dump
#   2. Full production restore (database + media):
#      sudo bash deploy/restore_backup.sh /var/backups/shop_pc/daily/db_shop_pc_prod_YYYYMMDD_HHMMSS.dump /var/backups/shop_pc/daily/media_YYYYMMDD_HHMMSS.tar.gz
# ==============================================================================

set -euo pipefail

APP_DIR="${APP_DIR:-/var/www/shop_pc}"
if [ -f "${APP_DIR}/.env" ]; then
    set -a
    # shellcheck disable=SC1090
    source "${APP_DIR}/.env"
    set +a
fi

DB_NAME="${DB_NAME:-shop_pc_prod}"
DB_USER="${DB_USER:-shop_pc_user}"
DB_HOST="${DB_HOST:-127.0.0.1}"
DB_PORT="${DB_PORT:-5432}"

if [ "${1:-}" = "--verify" ]; then
    DUMP_FILE="${2:?Error: Provide path to .dump file to verify}"
    VERIFY_DB="${DB_NAME}_verify_restore"
    echo "[$(date -Iseconds)] Verifying backup integrity into temporary database ${VERIFY_DB}..."
    sudo -u postgres psql -c "DROP DATABASE IF EXISTS ${VERIFY_DB};"
    sudo -u postgres psql -c "CREATE DATABASE ${VERIFY_DB} OWNER ${DB_USER};"
    PGPASSWORD="${DB_PASSWORD:-}" pg_restore -U "${DB_USER}" -h "${DB_HOST}" -p "${DB_PORT}" -d "${VERIFY_DB}" --no-owner --role="${DB_USER}" "${DUMP_FILE}"
    TABLE_COUNT="$(sudo -u postgres psql -tAc "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';" "${VERIFY_DB}")"
    sudo -u postgres psql -c "DROP DATABASE ${VERIFY_DB};"
    echo "[$(date -Iseconds)] SUCCESS: Backup verified cleanly (${TABLE_COUNT} public tables restored)."
    exit 0
fi

DUMP_FILE="${1:?Error: Provide path to PostgreSQL .dump file}"
MEDIA_ARCHIVE="${2:-}"

echo "[$(date -Iseconds)] Stopping Gunicorn service before production restore..."
systemctl stop shop_pc.service || true

echo "[$(date -Iseconds)] Restoring PostgreSQL database ${DB_NAME} from ${DUMP_FILE}..."
PGPASSWORD="${DB_PASSWORD:-}" pg_restore -U "${DB_USER}" -h "${DB_HOST}" -p "${DB_PORT}" -d "${DB_NAME}" --clean --if-exists --no-owner --role="${DB_USER}" "${DUMP_FILE}"

if [ -n "${MEDIA_ARCHIVE}" ] && [ -f "${MEDIA_ARCHIVE}" ]; then
    echo "[$(date -Iseconds)] Restoring media files from ${MEDIA_ARCHIVE}..."
    tar -xzf "${MEDIA_ARCHIVE}" -C "${APP_DIR}"
    chown -R www-data:www-data "${APP_DIR}/media"
fi

echo "[$(date -Iseconds)] Restarting Gunicorn service..."
systemctl start shop_pc.service
echo "[$(date -Iseconds)] Production restoration completed successfully."

