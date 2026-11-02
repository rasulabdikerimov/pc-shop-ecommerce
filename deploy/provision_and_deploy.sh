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
APP_DIR="/var/www/shop_pc"
LOG_DIR="/var/log/shop_pc"
BACKUP_DIR="/var/backups/shop_pc"
REPO_URL="https://github.com/rasulabdikerimov/pc-shop-ecommerce.git"
DB_NAME="shop_pc_prod"
DB_USER="shop_pc_user"
DB_PASS="$(openssl rand -hex 24)"

echo "==> [1/10] Updating Ubuntu packages and installing production stack..."
apt-get update && apt-get upgrade -y
apt-get install -y python3 python3-pip python3-venv python3-dev \
    postgresql postgresql-contrib libpq-dev \
    nginx certbot python3-certbot-nginx git ufw openssl

echo "==> [2/10] Configuring UFW Firewall (OpenSSH + Nginx Full only)..."
ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable

echo "==> [3/10] Configuring PostgreSQL database (${DB_NAME}) and user (${DB_USER})..."
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASS}';"
sudo -u postgres psql -c "ALTER USER ${DB_USER} WITH PASSWORD '${DB_PASS}';"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER} ENCODING 'UTF8' TEMPLATE template0;"
sudo -u postgres psql -c "ALTER ROLE ${DB_USER} SET client_encoding TO 'utf8';"
sudo -u postgres psql -c "ALTER ROLE ${DB_USER} SET default_transaction_isolation TO 'read committed';"
sudo -u postgres psql -c "ALTER ROLE ${DB_USER} SET timezone TO 'Asia/Tashkent';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};"

echo "==> [4/10] Preparing application directories and cloning ${REPO_URL}..."
mkdir -p "${APP_DIR}" "${LOG_DIR}" "${BACKUP_DIR}" /var/www/certbot
if [ ! -d "${APP_DIR}/.git" ]; then
    git clone "${REPO_URL}" "${APP_DIR}"
else
    cd "${APP_DIR}"
    git fetch origin main
    git reset --hard origin/main
fi

cd "${APP_DIR}"

echo "==> [5/10] Setting up Python virtual environment and installing dependencies..."
python3 -m venv "${APP_DIR}/venv"
"${APP_DIR}/venv/bin/pip" install --upgrade pip
"${APP_DIR}/venv/bin/pip" install -r "${APP_DIR}/requirements.txt"

echo "==> [6/10] Generating cryptographic .env configuration..."
DJANGO_SECRET="$("${APP_DIR}/venv/bin/python" -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")"
cat > "${APP_DIR}/.env" <<EOF
SECRET_KEY=${DJANGO_SECRET}
DEBUG=False
ALLOWED_HOSTS=${DOMAIN},www.${DOMAIN},localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://${DOMAIN},https://www.${DOMAIN}
DB_ENGINE=postgresql
DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASS}
DB_HOST=127.0.0.1
DB_PORT=5432
ENABLE_HTTPS=True
SECURE_SSL_REDIRECT=True
EOF
chmod 640 "${APP_DIR}/.env"

echo "==> [7/10] Running database migrations, seeding catalog, and collecting static files..."
"${APP_DIR}/venv/bin/python" manage.py migrate --noinput
"${APP_DIR}/venv/bin/python" manage.py seed_catalog
"${APP_DIR}/venv/bin/python" manage.py collectstatic --noinput

chown -R www-data:www-data "${APP_DIR}" "${LOG_DIR}" "${BACKUP_DIR}"

echo "==> [8/10] Installing and starting Gunicorn systemd service..."
cp "${APP_DIR}/deploy/shop_pc.service" /etc/systemd/system/shop_pc.service
systemctl daemon-reload
systemctl enable --now shop_pc.service

echo "==> [9/10] Configuring Nginx and Let's Encrypt HTTPS for ${DOMAIN}..."
sed "s/gshoptest.uz/${DOMAIN}/g" "${APP_DIR}/deploy/nginx_shop_pc.conf" > /etc/nginx/sites-available/shop_pc
ln -sf /etc/nginx/sites-available/shop_pc /etc/nginx/sites-enabled/shop_pc
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

if host "${DOMAIN}" >/dev/null 2>&1; then
    certbot --nginx -d "${DOMAIN}" -d "www.${DOMAIN}" --non-interactive --agree-tos -m "${ADMIN_EMAIL}" --redirect || true
fi

echo "==> [10/10] Configuring automated daily PostgreSQL & media backup cron job..."
chmod +x "${APP_DIR}/deploy/backup_db.sh"
(crontab -l 2>/dev/null | grep -v "backup_db.sh" || true; echo "0 3 * * * ${APP_DIR}/deploy/backup_db.sh >> ${LOG_DIR}/backup.log 2>&1") | crontab -

echo "=============================================================================="
echo " PC SHOP DEPLOYMENT COMPLETE!"
echo " Storefront URL: https://${DOMAIN}"
echo " Admin Portal:   https://${DOMAIN}/dashboard/"
echo "=============================================================================="

