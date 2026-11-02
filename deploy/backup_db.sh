#!/usr/bin/env bash
# Automated PostgreSQL & Media Backup Script for PC Shop
# Schedule via cron: 0 3 * * * /var/www/shop_pc/deploy/backup_db.sh >> /var/log/shop_pc/backup.log 2>&1

set -euo pipefail

BACKUP_DIR="/var/backups/shop_pc"
APP_DIR="/var/www/shop_pc"
DB_NAME="${DB_NAME:-shop_pc_prod}"
DB_USER="${DB_USER:-shop_pc_user}"
RETENTION_DAYS=14
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

mkdir -p "${BACKUP_DIR}"

echo "[$(date -Iseconds)] Starting PostgreSQL backup for ${DB_NAME}..."
pg_dump -U "${DB_USER}" -h 127.0.0.1 -Fc "${DB_NAME}" > "${BACKUP_DIR}/db_${DB_NAME}_${TIMESTAMP}.dump"

echo "[$(date -Iseconds)] Archiving uploaded media files..."
tar -czf "${BACKUP_DIR}/media_${TIMESTAMP}.tar.gz" -C "${APP_DIR}" media

echo "[$(date -Iseconds)] Pruning backups older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -type f -mtime +"${RETENTION_DAYS}" -delete

echo "[$(date -Iseconds)] Backup completed successfully."

