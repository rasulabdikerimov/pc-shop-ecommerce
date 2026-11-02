# PRODUCTION DEPLOYMENT & OPERATIONS GUIDE — PC Shop (`gshoptest.uz`)

This guide provides complete specifications and exact operational commands for deploying and maintaining the **PC Shop** Django e-commerce application in production from the existing GitHub repository:
`https://github.com/rasulabdikerimov/pc-shop-ecommerce.git`

---

## 1. Hosting Provider & Server Specifications

### Comparative Evaluation of Affordable Django VPS Providers

| Provider | Plan | vCPU / RAM | SSD / NVMe Storage | Bandwidth | Monthly Price | Ubuntu & Backup Support | Recommendation |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Hetzner Cloud** (Falkenstein / Helsinki) | **CX22** | 2 vCPU / 4 GB RAM | 40 GB NVMe | 20 TB | **€4.51 / mo** (~$4.90) | Ubuntu 24.04 LTS + automated daily snapshots (+20%) | **Selected Primary (Best Global Price / Performance)** |
| **Eskiz.uz / Ahost.uz** (Tashkent, Uzbekistan) | **VPS-Start / Cloud-2** | 2 vCPU / 2–4 GB RAM | 40 GB SSD | Unmetered TAS-IX | **95,000 UZS / mo** (~$7.50) | Ubuntu 24.04 LTS + ultra-low latency (<5ms TAS-IX) + Payme/Click billing | **Selected Regional Alternative (Uzbekistan TAS-IX)** |
| **Contabo** (EU / US) | **Cloud VPS 10** | 4 vCPU / 6 GB RAM | 100 GB SSD | 32 TB | **€4.50 / mo** (~$4.90) | Ubuntu 24.04 LTS + snapshot support | High RAM capacity per dollar |
| **DigitalOcean** (Frankfurt / AMS) | **Basic Droplet** | 1 vCPU / 2 GB RAM | 50 GB SSD | 2 TB | **$12.00 / mo** | Ubuntu 24.04 LTS + weekly snapshots | Simple global cloud infrastructure |

### Target Production Server Specifications
- **Operating System**: Ubuntu 24.04 LTS (64-bit)
- **CPU / RAM**: 2 vCPU / 4 GB RAM (+ 2 GB swap file fallback on <4 GB instances)
- **Storage**: 40 GB NVMe SSD
- **Timezone**: `Asia/Tashkent`
- **Database**: PostgreSQL 16 (`127.0.0.1:5432`, restricted to localhost only)
- **Application Server**: Gunicorn (`unix:/run/gunicorn/shop_pc.sock`, managed by `systemd` under `www-data`)
- **Web Server / Reverse Proxy**: Nginx 1.24+ with HTTP/2, Gzip compression, & Let's Encrypt TLS 1.2/1.3

---

## 2. Domain Availability & DNS Configuration (`gshoptest.uz`)

### Live WHOIS Verification (`whois.cctld.uz:43`)
- **`gshoptest.uz`**: **AVAILABLE** (Verified available for registration)
- **`pcshoptest.uz`**: **AVAILABLE** (Verified backup alternative)
- **`pcshop.uz`**: Registered (Unavailable)

### Registrar Comparison (`.uz` ccTLD)
| Accredited Registrar | Portal URL | Registration Price (1st Yr) | Renewal Price (Per Yr) | Payment Methods | DNS & SSL Support |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Eskiz.uz** (Recommended) | `https://my.eskiz.uz` | **28,000 UZS** (~$2.20) | **28,000 UZS** (~$2.20) | Payme, Click, Uzum, Corporate | Free DNS Manager + Let's Encrypt Ready |
| **Ahost.uz** | `https://ahost.uz/domains` | **29,000 UZS** (~$2.30) | **29,000 UZS** (~$2.30) | Payme, Click, Visa/Mastercard | Free DNS Manager + Let's Encrypt Ready |

### DNS Records
Configure the following DNS records in your registrar's DNS Zone Editor:
```text
Type    Name / Host    Value / Target           TTL
A       @              <YOUR_VPS_PUBLIC_IPV4>   3600
A       www            <YOUR_VPS_PUBLIC_IPV4>   3600
```

Verify DNS propagation before running Certbot:
```bash
dig +short A gshoptest.uz
dig +short A www.gshoptest.uz
```

---

## 3. One-Command Automated Provisioning & Deployment

You can provision a fresh Ubuntu 22.04 / 24.04 LTS server end-to-end with a single command using [`deploy/provision_and_deploy.sh`](file:///d:/Python/django/shop_pc/deploy/provision_and_deploy.sh):
```bash
git clone https://github.com/rasulabdikerimov/pc-shop-ecommerce.git /var/www/shop_pc
sudo bash /var/www/shop_pc/deploy/provision_and_deploy.sh gshoptest.uz admin@gshoptest.uz
```

Below is the step-by-step breakdown of everything configured by the script.

---

## 4. Server Preparation & Security Hardening

```bash
# 1. Update packages and enable unattended security upgrades
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y python3 python3-pip python3-venv python3-dev build-essential \
    postgresql postgresql-contrib libpq-dev \
    libjpeg-dev zlib1g-dev libwebp-dev \
    nginx certbot python3-certbot-nginx git ufw openssl unattended-upgrades rsync
sudo dpkg-reconfigure -f noninteractive unattended-upgrades

# 2. Set timezone and configure 2 GB swap space (if RAM < 4 GB)
sudo timedatectl set-timezone Asia/Tashkent
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# 3. Create non-root deployment user and harden SSH
sudo useradd -m -s /bin/bash -G sudo,www-data shop_pc
sudo sed -i 's/^#*PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
sudo sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo systemctl reload ssh

# 4. Configure UFW Firewall (Allow only SSH 22, HTTP 80, HTTPS 443; deny all other incoming ports)
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable
```

---

## 5. PostgreSQL Production Database Setup & Data Migration

Create the isolated production database and dedicated PostgreSQL user restricted to `127.0.0.1`:
```bash
sudo -u postgres psql << 'EOF'
CREATE USER shop_pc_user WITH PASSWORD 'ReplaceWithStrongDbPassword2026!';
CREATE DATABASE shop_pc_prod OWNER shop_pc_user ENCODING 'UTF8' TEMPLATE template0;
ALTER ROLE shop_pc_user SET client_encoding TO 'utf8';
ALTER ROLE shop_pc_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE shop_pc_user SET timezone TO 'Asia/Tashkent';
GRANT ALL PRIVILEGES ON DATABASE shop_pc_prod TO shop_pc_user;
\c shop_pc_prod
GRANT ALL ON SCHEMA public TO shop_pc_user;
EOF
```

### Safe SQLite to PostgreSQL Data Migration
If migrating an existing `db.sqlite3` database with user/order history into PostgreSQL, run [`deploy/migrate_sqlite_to_postgres.sh`](file:///d:/Python/django/shop_pc/deploy/migrate_sqlite_to_postgres.sh):
```bash
sudo bash /var/www/shop_pc/deploy/migrate_sqlite_to_postgres.sh /var/www/shop_pc/db.sqlite3
```

---

## 6. Deploying the Django Application

```bash
# 1. Create directories and clone repository
sudo mkdir -p /var/www/shop_pc /var/log/shop_pc /var/backups/shop_pc/daily /var/backups/shop_pc/weekly
git clone https://github.com/rasulabdikerimov/pc-shop-ecommerce.git /var/www/shop_pc
cd /var/www/shop_pc

# 2. Create virtual environment and install dependencies
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

# 3. Configure production .env file
cp .env.example .env
chmod 640 .env
```

Run migrations, seed the catalog, collect static files, and run Django's deployment security check:
```bash
cd /var/www/shop_pc
./venv/bin/python manage.py makemigrations --check --noinput
./venv/bin/python manage.py migrate --noinput
./venv/bin/python manage.py seed_catalog
./venv/bin/python manage.py collectstatic --noinput
./venv/bin/python manage.py check --deploy
sudo chown -R www-data:www-data /var/www/shop_pc /var/log/shop_pc /var/backups/shop_pc
```

---

## 7. Gunicorn & Nginx Configuration

### Gunicorn Systemd Service ([`deploy/shop_pc.service`](file:///d:/Python/django/shop_pc/deploy/shop_pc.service))
```bash
sudo cp /var/www/shop_pc/deploy/shop_pc.service /etc/systemd/system/shop_pc.service
sudo systemctl daemon-reload
sudo systemctl enable --now shop_pc.service
sudo systemctl status shop_pc.service
```

### Nginx Reverse Proxy & Let's Encrypt SSL ([`deploy/nginx_shop_pc.conf`](file:///d:/Python/django/shop_pc/deploy/nginx_shop_pc.conf))
```bash
sudo cp /var/www/shop_pc/deploy/nginx_shop_pc.conf /etc/nginx/sites-available/shop_pc
sudo ln -sf /etc/nginx/sites-available/shop_pc /etc/nginx/sites-enabled/shop_pc
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

# Issue Let's Encrypt SSL certificate and enable auto-renewal
sudo certbot --nginx -d gshoptest.uz -d www.gshoptest.uz --non-interactive --agree-tos -m admin@gshoptest.uz --redirect
sudo systemctl enable --now certbot.timer
sudo certbot renew --dry-run
```

---

## 8. Operations, Maintenance & Automated Backups

### 8.1 How to Update the Application from GitHub
```bash
cd /var/www/shop_pc
git fetch origin main
git reset --hard origin/main
./venv/bin/pip install -r requirements.txt
./venv/bin/python manage.py migrate --noinput
./venv/bin/python manage.py collectstatic --noinput
sudo systemctl restart shop_pc.service
```

### 8.2 How to Restart Services & View Logs
```bash
# Gunicorn service and logs
sudo systemctl restart shop_pc.service
sudo journalctl -u shop_pc.service -n 50 --no-pager
sudo tail -n 50 /var/log/shop_pc/gunicorn_error.log
sudo tail -n 50 /var/log/shop_pc/django.log

# Nginx service and logs
sudo nginx -t && sudo systemctl reload nginx
sudo tail -n 50 /var/log/nginx/error.log
```

### 8.3 Automated Database & Media Backups ([`deploy/backup_db.sh`](file:///d:/Python/django/shop_pc/deploy/backup_db.sh))
- **Schedule**: Daily at `03:00 AM` (`0 3 * * * /var/www/shop_pc/deploy/backup_db.sh >> /var/log/shop_pc/backup.log 2>&1`)
- **Retention**:
  - Last **7 daily backups** in `/var/backups/shop_pc/daily/`
  - Last **4 weekly backups** (28 days) in `/var/backups/shop_pc/weekly/`
- **Off-Server Backup Replication & Single-Server Risk**:
  - Storing backups only on `/var/backups/shop_pc` on the same VPS protects against accidental table deletion or bad migrations, **but does not protect against complete VPS disk failure or account loss**.
  - Set `REMOTE_BACKUP_TARGET` in `/var/www/shop_pc/.env` (e.g., `REMOTE_BACKUP_TARGET=s3:pcshop-backups` via `rclone` or `REMOTE_BACKUP_TARGET=backup@remote-host:/backups/shop_pc` via `rsync`) so [`deploy/backup_db.sh`](file:///d:/Python/django/shop_pc/deploy/backup_db.sh) automatically replicates every daily and weekly backup off-server.

### 8.4 How to Verify & Restore Backups ([`deploy/restore_backup.sh`](file:///d:/Python/django/shop_pc/deploy/restore_backup.sh))
```bash
# 1. Non-destructive test restore into a temporary verification database
sudo bash /var/www/shop_pc/deploy/restore_backup.sh --verify /var/backups/shop_pc/daily/db_shop_pc_prod_<TIMESTAMP>.dump

# 2. Full production database & media restoration
sudo bash /var/www/shop_pc/deploy/restore_backup.sh \
    /var/backups/shop_pc/daily/db_shop_pc_prod_<TIMESTAMP>.dump \
    /var/backups/shop_pc/daily/media_<TIMESTAMP>.tar.gz
```

---

## 9. Troubleshooting Common Issues
- **`502 Bad Gateway` in Nginx**: Check `sudo systemctl status shop_pc.service` and `/var/log/shop_pc/gunicorn_error.log`. Verify `/run/gunicorn/shop_pc.sock` exists and `www-data` owns `/var/www/shop_pc`.
- **`400 Bad Request` on Domain**: Verify `ALLOWED_HOSTS` in `/var/www/shop_pc/.env` includes both `gshoptest.uz` and `www.gshoptest.uz`, then run `sudo systemctl restart shop_pc.service`.
- **`403 Forbidden` on Form Submission (CSRF)**: Verify `CSRF_TRUSTED_ORIGINS=https://gshoptest.uz,https://www.gshoptest.uz` is set in `.env` and Nginx forwards `X-Forwarded-Proto $scheme`.
