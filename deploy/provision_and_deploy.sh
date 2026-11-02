#!/usr/bin/env bash
# ==============================================================================
# PC SHOP — AUTOMATED UBUNTU PRODUCTION SERVER PROVISIONING & DEPLOYMENT SCRIPT
# Repository: https://github.com/rasulabdikerimov/pc-shop-ecommerce.git
# Usage: sudo bash deploy/provision_and_deploy.sh [domain] [admin_email]
# Example: sudo bash deploy/provision_and_deploy.sh gshoptest.uz admin@gshoptest.uz
# ==============================================================================

set -euo pipefail

DOMAIN="${1:-gshoptest.uz}"
ADMIN_EMAIL="${2:-admin@${DOMAIN}}"
DEPLOY_USER="shop_pc"
APP_DIR="/var/www/shop_pc"
LOG_DIR="/var/log/shop_pc"
BACKUP_DIR="/var/backups/shop_pc"
REPO_URL="https://github.com/rasulabdikerimov/pc-shop-ecommerce.git"
DB_NAME="shop_pc_prod"
DB_USER="shop_pc_user"
DB_PASS="$(openssl rand -hex 24)"

echo "==> [1/12] Updating Ubuntu packages and enabling automatic security updates..."
export DEBIAN_FRONTEND=noninteractive
apt-get update && apt-get upgrade -y
apt-get install -y python3 python3-pip python3-venv python3-dev build-essential \
    postgresql postgresql-contrib libpq-dev \
    libjpeg-dev zlib1g-dev libwebp-dev \
    nginx certbot python3-certbot-nginx git ufw openssl unattended-upgrades rsync

dpkg-reconfigure -f noninteractive unattended-upgrades || true

echo "==> [2/12] Setting server timezone to Asia/Tashkent and configuring Swap..."
timedatectl set-timezone Asia/Tashkent || true

TOTAL_MEM_MB="$(awk '/MemTotal/ {print int($2/1024)}' /proc/meminfo)"
if [ "${TOTAL_MEM_MB}" -lt 4096 ] && [ ! -f /swapfile ]; then
    echo "Creating 2 GB swap file for low-memory VPS (${TOTAL_MEM_MB} MB RAM)..."
    fallocate -l 2G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=2048
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

echo "==> [3/12] Creating non-root deployment user (${DEPLOY_USER}) and hardening SSH..."
if ! id -u "${DEPLOY_USER}" >/dev/null 2>&1; then
    useradd -m -s /bin/bash -G sudo,www-data "${DEPLOY_USER}"
fi
if [ -d /root/.ssh ]; then
    mkdir -p "/home/${DEPLOY_USER}/.ssh"
    cp -n /root/.ssh/authorized_keys "/home/${DEPLOY_USER}/.ssh/authorized_keys" 2>/dev/null || true
    chown -R "${DEPLOY_USER}:${DEPLOY_USER}" "/home/${DEPLOY_USER}/.ssh"
    chmod 700 "/home/${DEPLOY_USER}/.ssh"
    chmod 600 "/home/${DEPLOY_USER}/.ssh/authorized_keys" 2>/dev/null || true
fi
if [ -s "/root/.ssh/authorized_keys" ]; then
    sed -i 's/^#*PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
    sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
    systemctl reload ssh || systemctl reload sshd || true
fi

echo "==> [4/12] Configuring UFW Firewall (SSH 22, HTTP 80, HTTPS 443 only)..."
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo "==> [5/12] Configuring PostgreSQL database (${DB_NAME}) and user (${DB_USER})..."
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASS}';"
sudo -u postgres psql -c "ALTER USER ${DB_USER} WITH PASSWORD '${DB_PASS}';"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER} ENCODING 'UTF8' TEMPLATE template0;"
sudo -u postgres psql -c "ALTER ROLE ${DB_USER} SET client_encoding TO 'utf8';"
sudo -u postgres psql -c "ALTER ROLE ${DB_USER} SET default_transaction_isolation TO 'read committed';"
sudo -u postgres psql -c "ALTER ROLE ${DB_USER} SET timezone TO 'Asia/Tashkent';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};"
sudo -u postgres psql -d "${DB_NAME}" -c "GRANT ALL ON SCHEMA public TO ${DB_USER};"

echo "==> [6/12] Preparing application directories and cloning ${REPO_URL}..."
mkdir -p "${APP_DIR}" "${LOG_DIR}" "${BACKUP_DIR}/daily" "${BACKUP_DIR}/weekly" /var/www/certbot
if [ ! -d "${APP_DIR}/.git" ]; then
    git clone "${REPO_URL}" "${APP_DIR}"
else
    cd "${APP_DIR}"
    git fetch origin main
    git reset --hard origin/main
fi

cd "${APP_DIR}"

echo "==> [7/12] Setting up Python virtual environment and installing dependencies..."
python3 -m venv "${APP_DIR}/venv"
"${APP_DIR}/venv/bin/pip" install --upgrade pip
"${APP_DIR}/venv/bin/pip" install -r "${APP_DIR}/requirements.txt"

echo "==> [8/12] Generating cryptographic .env configuration..."
SERVER_IP="$(hostname -I | awk '{print $1}')"
DJANGO_SECRET="$("${APP_DIR}/venv/bin/python" -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")"
cat > "${APP_DIR}/.env" <<EOF
SECRET_KEY=${DJANGO_SECRET}
DEBUG=False
ALLOWED_HOSTS=${DOMAIN},www.${DOMAIN},${SERVER_IP},localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://${DOMAIN},https://www.${DOMAIN},http://${SERVER_IP}
DB_ENGINE=postgresql
DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASS}
DB_HOST=127.0.0.1
DB_PORT=5432
ENABLE_HTTPS=True
SECURE_SSL_REDIRECT=True
DJANGO_LOG_LEVEL=INFO
DJANGO_LOG_FILE=${LOG_DIR}/django.log
REMOTE_BACKUP_TARGET=
EOF
chmod 640 "${APP_DIR}/.env"

echo "==> [9/12] Running database migrations, seeding catalog, and collecting static files..."
"${APP_DIR}/venv/bin/python" manage.py makemigrations --check --noinput
if [ -f "${APP_DIR}/db.sqlite3" ]; then
    chmod +x "${APP_DIR}/deploy/migrate_sqlite_to_postgres.sh"
    bash "${APP_DIR}/deploy/migrate_sqlite_to_postgres.sh" "${APP_DIR}/db.sqlite3"
else
    "${APP_DIR}/venv/bin/python" manage.py migrate --noinput
    "${APP_DIR}/venv/bin/python" manage.py seed_catalog
fi
"${APP_DIR}/venv/bin/python" manage.py collectstatic --noinput
"${APP_DIR}/venv/bin/python" manage.py check --deploy

chown -R www-data:www-data "${APP_DIR}" "${LOG_DIR}" "${BACKUP_DIR}"
chmod -R 750 "${BACKUP_DIR}"

echo "==> [10/12] Installing and starting Gunicorn systemd service..."
cp "${APP_DIR}/deploy/shop_pc.service" /etc/systemd/system/shop_pc.service
systemctl daemon-reload
systemctl enable --now shop_pc.service

echo "==> [11/12] Configuring Nginx and Let's Encrypt HTTPS for ${DOMAIN}..."
sed "s/gshoptest.uz/${DOMAIN}/g" "${APP_DIR}/deploy/nginx_shop_pc.conf" > /etc/nginx/sites-available/shop_pc
ln -sf /etc/nginx/sites-available/shop_pc /etc/nginx/sites-enabled/shop_pc
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

if host "${DOMAIN}" >/dev/null 2>&1; then
    certbot --nginx -d "${DOMAIN}" -d "www.${DOMAIN}" --non-interactive --agree-tos -m "${ADMIN_EMAIL}" --redirect || true
    systemctl enable --now certbot.timer || true
fi

echo "==> [12/12] Configuring automated daily/weekly PostgreSQL & media backups and testing restore..."
chmod +x "${APP_DIR}/deploy/backup_db.sh" "${APP_DIR}/deploy/restore_backup.sh" "${APP_DIR}/deploy/migrate_sqlite_to_postgres.sh"
"${APP_DIR}/deploy/backup_db.sh"
LATEST_DUMP="$(ls -t "${BACKUP_DIR}/daily"/db_*.dump | head -n 1)"
if [ -n "${LATEST_DUMP}" ]; then
    "${APP_DIR}/deploy/restore_backup.sh" --verify "${LATEST_DUMP}"
fi
(crontab -l 2>/dev/null | grep -v "backup_db.sh" || true; echo "0 3 * * * ${APP_DIR}/deploy/backup_db.sh >> ${LOG_DIR}/backup.log 2>&1") | crontab -

echo "=============================================================================="
echo " PC SHOP DEPLOYMENT COMPLETE!"
echo " Storefront URL: https://${DOMAIN} (or http://${SERVER_IP})"
echo " Admin Portal:   https://${DOMAIN}/dashboard/"
echo "=============================================================================="
