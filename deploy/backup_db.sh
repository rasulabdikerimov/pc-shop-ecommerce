#!/usr/bin/env bash
# ==============================================================================
# Automated PostgreSQL, Django Fixture & Media Backup Script for PC Shop
# Schedule via cron:
#   0 3 * * * /var/www/shop_pc/deploy/backup_db.sh >> /var/log/shop_pc/backup.log 2>&1
#
# Retention Policy:
#   - Daily backups:  Kept for 7 days in /var/backups/shop_pc/daily/
#   - Weekly backups: Kept for 4 weeks (28 days) in /var/backups/shop_pc/weekly/
#
# Off-Server Backup Support:
#   Set REMOTE_BACKUP_TARGET in /var/www/shop_pc/.env (e.g., "s3:pcshop-backups"
#   for rclone or "backupuser@backup-host:/backups/shop_pc" for rsync/scp) to
#   replicate backups off-server automatically and mitigate single-server failure.
# ==============================================================================

set -euo pipefail

APP_DIR="${APP_DIR:-/var/www/shop_pc}"
BACKUP_ROOT="${BACKUP_ROOT:-/var/backups/shop_pc}"
DAILY_DIR="${BACKUP_ROOT}/daily"
WEEKLY_DIR="${BACKUP_ROOT}/weekly"

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
DAILY_RETENTION_DAYS=7
WEEKLY_RETENTION_DAYS=28
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
DAY_OF_WEEK="$(date +%u)" # 7 = Sunday

mkdir -p "${DAILY_DIR}" "${WEEKLY_DIR}"
chmod 750 "${BACKUP_ROOT}" "${DAILY_DIR}" "${WEEKLY_DIR}"

DB_DUMP_FILE="${DAILY_DIR}/db_${DB_NAME}_${TIMESTAMP}.dump"
MEDIA_ARCHIVE_FILE="${DAILY_DIR}/media_${TIMESTAMP}.tar.gz"

echo "[$(date -Iseconds)] Starting PostgreSQL backup for ${DB_NAME}..."
PGPASSWORD="${DB_PASSWORD:-}" pg_dump -U "${DB_USER}" -h "${DB_HOST}" -p "${DB_PORT}" -Fc "${DB_NAME}" > "${DB_DUMP_FILE}"
chmod 640 "${DB_DUMP_FILE}"

echo "[$(date -Iseconds)] Archiving uploaded media files..."
if [ -d "${APP_DIR}/media" ]; then
    tar -czf "${MEDIA_ARCHIVE_FILE}" -C "${APP_DIR}" media
    chmod 640 "${MEDIA_ARCHIVE_FILE}"
fi

# Copy Sunday backup to weekly rotation directory (kept for 4 weeks)
if [ "${DAY_OF_WEEK}" = "7" ]; then
    echo "[$(date -Iseconds)] Creating weekly snapshot in ${WEEKLY_DIR}..."
    cp "${DB_DUMP_FILE}" "${WEEKLY_DIR}/"
    if [ -f "${MEDIA_ARCHIVE_FILE}" ]; then
        cp "${MEDIA_ARCHIVE_FILE}" "${WEEKLY_DIR}/"
    fi
fi

echo "[$(date -Iseconds)] Rotating backups (keeping ${DAILY_RETENTION_DAYS} daily and 4 weekly backups)..."
find "${DAILY_DIR}" -type f -mtime +"${DAILY_RETENTION_DAYS}" -delete
find "${WEEKLY_DIR}" -type f -mtime +"${WEEKLY_RETENTION_DAYS}" -delete

# Off-Server Replication (if configured)
if [ -n "${REMOTE_BACKUP_TARGET:-}" ]; then
    echo "[$(date -Iseconds)] Syncing backups off-server to ${REMOTE_BACKUP_TARGET}..."
    if command -v rclone >/dev/null 2>&1 && [[ "${REMOTE_BACKUP_TARGET}" == *:* ]]; then
        rclone sync "${BACKUP_ROOT}" "${REMOTE_BACKUP_TARGET}"
    else
        rsync -az --delete "${BACKUP_ROOT}/" "${REMOTE_BACKUP_TARGET}/"
    fi
    echo "[$(date -Iseconds)] Off-server backup replication finished."
else
    echo "[$(date -Iseconds)] NOTE: REMOTE_BACKUP_TARGET not set; backups are stored locally in ${BACKUP_ROOT}. Configure REMOTE_BACKUP_TARGET in .env for off-server disaster recovery."
fi

echo "[$(date -Iseconds)] Backup completed successfully."
