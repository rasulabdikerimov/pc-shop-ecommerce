# PRODUCTION DEPLOYMENT & OPERATIONS GUIDE — PC Shop (`gshoptest.uz`)

This guide provides complete specifications and exact operational commands for deploying and maintaining the **PC Shop** Django e-commerce application in production from the official repository:
`https://github.com/rasulabdikerimov/pc-shop-ecommerce.git`

---

## 1. Hosting Provider & Server Specifications

### Comparative Evaluation of Affordable Django VPS Providers

| Provider | Plan | vCPU / RAM | SSD / NVMe Storage | Bandwidth | Monthly Price | PostgreSQL & Backup Support | Recommendation |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Hetzner Cloud** (Falkenstein / Helsinki) | **CX22** | 2 vCPU / 4 GB RAM | 40 GB NVMe | 20 TB | **€4.51 / mo** (~$4.90) | Ubuntu 24.04 LTS + automated daily backups (+20%) | **Best Overall Price / Performance** |
| **Eskiz.uz / Ahost.uz** (Tashkent, Uzbekistan) | **VPS-Start / Cloud-2** | 2 vCPU / 2–4 GB RAM | 40 GB SSD | Unmetered TAS-IX | **95,000 – 140,000 UZS / mo** (~$7.50–$11) | Ultra-low latency in Uzbekistan (<5ms TAS-IX) + Payme/Click billing | **Best for Local Uzbekistan TAS-IX Speed** |
| **DigitalOcean** (Frankfurt / Bangalore) | **Basic Droplet** | 1 vCPU / 2 GB RAM | 50 GB SSD | 2 TB | **$12.00 / mo** | Ubuntu 24.04 LTS + weekly snapshots | Simple global cloud infrastructure |

### Target Production Server Specifications
- **Operating System**: Ubuntu 24.04 LTS (64-bit)
- **CPU / RAM**: 2 vCPU / 4 GB RAM
- **Storage**: 40 GB NVMe SSD
- **Database**: PostgreSQL 16 (`127.0.0.1:5432`, bound to localhost only)
- **Application Server**: Gunicorn (`unix:/run/gunicorn/shop_pc.sock`, managed by `systemd`)
- **Web Server / Reverse Proxy**: Nginx 1.24+ with HTTP/2 & Let's Encrypt TLS 1.2/1.3

---

## 2. Domain Availability & Registration (`gshoptest.uz`)

### Live WHOIS Verification (`whois.cctld.uz`)
We queried the official `.uz` registry (`whois.cctld.uz:43`) directly:
- **`gshoptest.uz`**: **AVAILABLE** (Verified available for immediate registration)
- **`pcshoptest.uz`**: **AVAILABLE** (Verified backup alternative)
- **`pcshop.uz`**: Registered (Unavailable)

### Registrar Comparison (`.uz` ccTLD)
| Accredited Registrar | Portal URL | Registration Price (1st Yr) | Renewal Price (Per Yr) | Payment Methods | DNS & SSL Support |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Eskiz.uz** (Recommended) | `https://my.eskiz.uz` | **28,000 UZS** (~$2.20) | **28,000 UZS** (~$2.20) | Payme, Click, Uzum, Corporate | Free DNS Manager + Let's Encrypt Ready |
| **Ahost.uz** | `https://ahost.uz/domains` | **29,000 UZS** (~$2.30) | **29,000 UZS** (~$2.30) | Payme, Click, Visa/Mastercard | Free DNS Manager + Let's Encrypt Ready |
| **Billur COM** | `https://billur.com` | **33,000 UZS** (~$2.60) | **33,000 UZS** (~$2.60) | Payme, Click, Bank Transfer | Full DNS Zone Editor |

### DNS Configuration
Once registered, configure the following DNS records in the registrar's DNS Zone Editor:
```text
Type    Name / Host    Value / Target           TTL
A       @              <YOUR_VPS_PUBLIC_IPV4>   3600
A       www            <YOUR_VPS_PUBLIC_IPV4>   3600
```

---

## 3. Initial Server Preparation & Security Hardening

SSH into your Ubuntu LTS server and execute:
```bash
# 1. Update packages and install system dependencies
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv python3-dev \
    postgresql postgresql-contrib libpq-dev \
    nginx certbot python3-certbot-nginx git ufw

# 2. Configure UFW Firewall (Allow only SSH, HTTP, and HTTPS; keep PostgreSQL 5432 closed externally)
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw --force enable
sudo ufw status
```

---

## 4. PostgreSQL Production Database Setup

Create the isolated production database and dedicated PostgreSQL user:
```bash
sudo -u postgres psql << 'EOF'
CREATE USER shop_pc_user WITH PASSWORD 'ReplaceWithStrongDbPassword2026!';
CREATE DATABASE shop_pc_prod OWNER shop_pc_user ENCODING 'UTF8' LC_COLLATE 'en_US.UTF-8' LC_CTYPE 'en_US.UTF-8' TEMPLATE template0;
ALTER ROLE shop_pc_user SET client_encoding TO 'utf8';
ALTER ROLE shop_pc_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE shop_pc_user SET timezone TO 'Asia/Tashkent';
GRANT ALL PRIVILEGES ON DATABASE shop_pc_prod TO shop_pc_user;
EOF
```

---

## 5. Deploying the Application from the New GitHub Repository

```bash
# 1. Create application and log directories
sudo mkdir -p /var/www/shop_pc /var/log/shop_pc /var/backups/shop_pc
sudo chown -R $USER:www-data /var/www/shop_pc /var/log/shop_pc

# 2. Clone the new GitHub repository
git clone https://github.com/rasulabdikerimov/pc-shop-ecommerce.git /var/www/shop_pc
cd /var/www/shop_pc

# 3. Create virtual environment and install dependencies
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

# 4. Generate production .env file
cp .env.example .env
chmod 640 .env
```

Generate a fresh 50-character `SECRET_KEY`:
```bash
./venv/bin/python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Edit `/var/www/shop_pc/.env` with your production values:
```ini
SECRET_KEY=<paste-generated-secret-key>
DEBUG=False
ALLOWED_HOSTS=gshoptest.uz,www.gshoptest.uz,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://gshoptest.uz,https://www.gshoptest.uz

DB_ENGINE=postgresql
DB_NAME=shop_pc_prod
DB_USER=shop_pc_user
DB_PASSWORD=ReplaceWithStrongDbPassword2026!
DB_HOST=127.0.0.1
DB_PORT=5432

ENABLE_HTTPS=True
SECURE_SSL_REDIRECT=True
```

Run database migrations, seed initial hardware catalog, collect static files, and create the administrative superuser:
```bash
cd /var/www/shop_pc
./venv/bin/python manage.py migrate --noinput
./venv/bin/python manage.py seed_catalog
./venv/bin/python manage.py collectstatic --noinput
./venv/bin/python manage.py createsuperuser

sudo chown -R www-data:www-data /var/www/shop_pc/media /var/www/shop_pc/staticfiles /var/log/shop_pc
```

---

## 6. Gunicorn & Systemd Service Setup

Install and start the `shop_pc` systemd service ([`deploy/shop_pc.service`](file:///d:/Python/django/shop_pc/deploy/shop_pc.service)):
```bash
sudo cp /var/www/shop_pc/deploy/shop_pc.service /etc/systemd/system/shop_pc.service
sudo systemctl daemon-reload
sudo systemctl enable --now shop_pc.service
sudo systemctl status shop_pc.service
```

---

## 7. Nginx & Let's Encrypt HTTPS Configuration

The Nginx configuration ([`deploy/nginx_shop_pc.conf`](file:///d:/Python/django/shop_pc/deploy/nginx_shop_pc.conf)) enforces:
- HTTP (`80`) &rarr; `301` redirect to `https://gshoptest.uz$request_uri`
- `https://www.gshoptest.uz` &rarr; `301` redirect to canonical `https://gshoptest.uz$request_uri`
- Direct static (`/static/`) and media (`/media/`) file serving with cache headers

```bash
# 1. Enable Nginx site configuration
sudo cp /var/www/shop_pc/deploy/nginx_shop_pc.conf /etc/nginx/sites-available/shop_pc
sudo ln -sf /etc/nginx/sites-available/shop_pc /etc/nginx/sites-enabled/shop_pc
sudo rm -f /etc/nginx/sites-enabled/default

# 2. Issue Let's Encrypt SSL certificate for both gshoptest.uz and www.gshoptest.uz
sudo certbot --nginx -d gshoptest.uz -d www.gshoptest.uz --non-interactive --agree-tos -m admin@gshoptest.uz

# 3. Verify automatic SSL renewal timer and reload Nginx
sudo systemctl status certbot.timer
sudo nginx -t
sudo systemctl reload nginx
```

---

## 8. Operations, Maintenance & Backup Restoration

### 8.1 How to Update the Live Application
```bash
cd /var/www/shop_pc
git fetch origin main
git reset --hard origin/main
./venv/bin/pip install -r requirements.txt
./venv/bin/python manage.py migrate --noinput
./venv/bin/python manage.py collectstatic --noinput
sudo systemctl restart shop_pc.service
```

### 8.2 How to Restart Services & Inspect Logs
```bash
# Restart Gunicorn application server
sudo systemctl restart shop_pc.service
sudo journalctl -u shop_pc.service -n 50 --no-pager

# Reload or restart Nginx
sudo nginx -t && sudo systemctl reload nginx
sudo tail -n 50 /var/log/shop_pc/gunicorn_error.log
```

### 8.3 How to Run Database Migrations
```bash
cd /var/www/shop_pc
./venv/bin/python manage.py migrate --noinput
```

### 8.4 Automated Backups & How to Restore a Database Backup
Enable the daily 03:00 AM backup cron job ([`deploy/backup_db.sh`](file:///d:/Python/django/shop_pc/deploy/backup_db.sh)):
```bash
sudo chmod +x /var/www/shop_pc/deploy/backup_db.sh
(crontab -l 2>/dev/null; echo "0 3 * * * /var/www/shop_pc/deploy/backup_db.sh >> /var/log/shop_pc/backup.log 2>&1") | crontab -
```

To restore a PostgreSQL backup (`.dump`) and media archive (`.tar.gz`):
```bash
# Stop application traffic during restoration
sudo systemctl stop shop_pc.service

# Restore PostgreSQL database from custom-format dump
pg_restore -U shop_pc_user -h 127.0.0.1 -d shop_pc_prod --clean --if-exists /var/backups/shop_pc/db_shop_pc_prod_<TIMESTAMP>.dump

# Restore media directory
tar -xzf /var/backups/shop_pc/media_<TIMESTAMP>.tar.gz -C /var/www/shop_pc/
sudo chown -R www-data:www-data /var/www/shop_pc/media

# Restart application
sudo systemctl start shop_pc.service
```
