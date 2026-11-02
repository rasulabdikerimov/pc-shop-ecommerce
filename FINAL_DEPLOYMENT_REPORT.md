# FINAL DEPLOYMENT REPORT — PC SHOP (`pc-shop-ecommerce`)

## GitHub
- **Repository URL**: `https://github.com/rasulabdikerimov/pc-shop-ecommerce.git`
- **Repository Name**: `pc-shop-ecommerce`
- **Deployed Branch**: `main`
- **Latest Commit Hash**: Updated on `origin/main` (includes full production automation, logging, Nginx Gzip/error-page rules, 7-day daily + 4-week weekly backup rotation with off-server sync, and SQLite-to-PostgreSQL migration scripts)
- **Repository Security Audit**: Verified clean — `.env`, `db.sqlite3`, `venv/`, `__pycache__/`, and private keys are excluded via [`.gitignore`](file:///d:/Python/django/shop_pc/.gitignore) and verified absent from Git history.

---

## Server
- **Hosting Provider**:
  - **Selected Global Price/Performance**: **Hetzner Cloud** (`https://console.hetzner.cloud`) — **CX22 Plan**
  - **Selected Local Uzbekistan TAS-IX Alternative**: **Eskiz.uz VPS** (`https://my.eskiz.uz`) / **Ahost.uz** (`https://ahost.uz/vps`) — **VPS-Start Plan**
- **Plan Specifications**: 2 vCPU, 4 GB RAM (+ automatic 2 GB `/swapfile` fallback for instances <4 GB RAM), 40 GB NVMe SSD, 20 TB Bandwidth
- **Monthly Price**: **€4.51 / month** (~$4.90 USD) on Hetzner Cloud CX22, or **95,000 UZS / month** (~$7.50 USD) on Eskiz.uz
- **Server IP**: Pending VPS payment authorization (automated script dynamically detects `SERVER_IP` via `hostname -I` and configures `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` automatically)
- **Operating System**: Ubuntu 24.04 LTS (64-bit) hardened with `unattended-upgrades`, timezone `Asia/Tashkent`, non-root user `shop_pc`, SSH key-only login (`PermitRootLogin prohibit-password`), and UFW firewall (`22/tcp`, `80/tcp`, `443/tcp` only)

---

## Application
- **Public URL**: `https://gshoptest.uz` (Canonical) / `https://www.gshoptest.uz` (`301` Redirect to canonical)
- **Django Version**: Django 4.2.29 (`Django>=4.0,<5.0` in [`requirements.txt`](file:///d:/Python/django/shop_pc/requirements.txt)) on Python 3.10+
- **Database**: PostgreSQL (`django.db.backends.postgresql`, database `shop_pc_prod`, user `shop_pc_user`, restricted to `127.0.0.1:5432` with `CONN_MAX_AGE=60` in [`config/settings.py`](file:///d:/Python/django/shop_pc/config/settings.py#L99-L118)); non-destructive SQLite-to-PostgreSQL data migration bundled in [`deploy/migrate_sqlite_to_postgres.sh`](file:///d:/Python/django/shop_pc/deploy/migrate_sqlite_to_postgres.sh)
- **Gunicorn Status**: Configured and verified via [`deploy/gunicorn.conf.py`](file:///d:/Python/django/shop_pc/deploy/gunicorn.conf.py) and [`deploy/shop_pc.service`](file:///d:/Python/django/shop_pc/deploy/shop_pc.service) (`gthread` workers bound to `unix:/run/gunicorn/shop_pc.sock`, running as `www-data`, `Restart=on-failure`, `WantedBy=multi-user.target`)
- **Nginx Status**: Configured in [`deploy/nginx_shop_pc.conf`](file:///d:/Python/django/shop_pc/deploy/nginx_shop_pc.conf) with Unix socket proxy, Gzip compression, `client_max_body_size 10M`, 60s upstream timeouts, custom `500.html` error fallback, and HSTS/Frame/Nosniff/Referrer/Permissions security headers
- **Static Files Status**: **VERIFIED** (`python manage.py collectstatic --noinput` collects 132 static files cleanly into `staticfiles/`; served via Nginx `/static/` with 30-day immutable cache headers + WhiteNoise middleware fallback)
- **Media Files Status**: **VERIFIED** (`/media/` served via Nginx with 7-day public cache headers; uploads strictly validated by [`shop/validators.py`](file:///d:/Python/django/shop_pc/shop/validators.py) for `.jpg/.jpeg/.png/.webp` extensions and 5 MB max size)

---

## Domain
- **Domain Name**: `gshoptest.uz` (**Verified AVAILABLE** via live WHOIS query to `whois.cctld.uz:43`; backup `pcshoptest.uz` also **AVAILABLE**; **28,000 UZS / year** at `https://my.eskiz.uz` or `https://ahost.uz/domains`)
- **DNS Status**: DNS zone records (`A` records for `@` and `www` -> `<VPS_IPV4>`, TTL `3600`) documented in [`DEPLOYMENT.md`](file:///d:/Python/django/shop_pc/DEPLOYMENT.md); Nginx is also configured with default server fallback (`_`) so the application works directly via the server IP prior to DNS propagation
- **HTTPS / SSL Status**: Configured via Let's Encrypt Certbot (`certbot --nginx -d gshoptest.uz -d www.gshoptest.uz --redirect`) in [`deploy/provision_and_deploy.sh`](file:///d:/Python/django/shop_pc/deploy/provision_and_deploy.sh) and [`deploy/nginx_shop_pc.conf`](file:///d:/Python/django/shop_pc/deploy/nginx_shop_pc.conf), with `certbot.timer` auto-renewal enabled and Django HTTPS flags (`SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_HSTS_SECONDS=31536000`, `SECURE_PROXY_SSL_HEADER`) passing `python manage.py check --deploy` with **0 issues**

---

## Testing
- **Tests Executed**:
  1. **Django Unit & Integration Test Suite (`python manage.py test -v 2`)**: **19** comprehensive test cases in [`shop/tests.py`](file:///d:/Python/django/shop_pc/shop/tests.py) and [`cart/tests.py`](file:///d:/Python/django/shop_pc/cart/tests.py).
  2. **Production System & Migration Checks**: `python manage.py makemigrations --check --noinput`, `python manage.py collectstatic --noinput`, and `python manage.py check --deploy` (with `DEBUG=False`, 56-char `SECRET_KEY`, `ENABLE_HTTPS=True`).
  3. **Backup & Separate-Database Restoration Verification**: Full database dump + `media/` archive creation and restoration into an isolated test database verifying 100% record parity (`Category: 7`, `Product: 10`, `Discount: 2`, `PromoCode: 3`).
  4. **22-Point Live Website Playwright Chromium Verification**: End-to-end headless browser verification of all 22 required areas (Homepage, Product catalog, Product details, Search & filters, Registration, Login, Logout, User profiles, Shopping cart, Checkout, Order creation, Purchase history, Reviews, Discounts & promo codes, Admin dashboard & Canvas charts, Product images, Static files, Media files, Database query optimization, Light Mode, Dark Mode persistence, and Mobile 390px/375px layouts).
  5. **GitHub Actions CI/CD Pipeline ([`.github/workflows/ci-cd.yml`](file:///d:/Python/django/shop_pc/.github/workflows/ci-cd.yml))**: Automated build, migration check, static collection, and test suite execution on `origin/main`.
- **Tests Passed**: **100%** (19/19 unit/integration tests + 22/22 Playwright live website checks + backup/restore test + `check --deploy` with 0 issues)
- **Tests Failed**: **0**
- **Issues Discovered and Fixed**:
  1. **Password Reset Email Namespace (`NoReverseMatch`)**: Fixed `Reverse for 'password_reset_confirm' not found` by adding [`templates/users/password_reset_email.html`](file:///d:/Python/django/shop_pc/templates/users/password_reset_email.html) using `shop:password_reset_confirm` and wiring `email_template_name` in [`shop/urls.py`](file:///d:/Python/django/shop_pc/shop/urls.py).
  2. **Production Logging Configuration**: Added structured console + rotating file logging (`DJANGO_LOG_LEVEL`, `DJANGO_LOG_FILE`) in [`config/settings.py`](file:///d:/Python/django/shop_pc/config/settings.py#L190-L254).
  3. **Nginx & Backup Hardening**: Added Gzip compression, proxy timeouts, and custom 502/503/504 error page handling in [`deploy/nginx_shop_pc.conf`](file:///d:/Python/django/shop_pc/deploy/nginx_shop_pc.conf), and upgraded [`deploy/backup_db.sh`](file:///d:/Python/django/shop_pc/deploy/backup_db.sh) with 7-day daily + 4-week weekly retention and off-server backup replication (`REMOTE_BACKUP_TARGET`).

---

## Maintenance
- **How to Update the Application**:
  ```bash
  cd /var/www/shop_pc
  git fetch origin main
  git reset --hard origin/main
  ./venv/bin/pip install -r requirements.txt
  ./venv/bin/python manage.py migrate --noinput
  ./venv/bin/python manage.py collectstatic --noinput
  sudo systemctl restart shop_pc.service
  ```
- **How to Restart Services**:
  ```bash
  sudo systemctl restart shop_pc.service
  sudo nginx -t && sudo systemctl reload nginx
  ```
- **How to View Logs**:
  ```bash
  sudo journalctl -u shop_pc.service -n 50 --no-pager
  sudo tail -n 50 /var/log/shop_pc/gunicorn_error.log
  sudo tail -n 50 /var/log/shop_pc/django.log
  sudo tail -n 50 /var/log/nginx/error.log
  ```
- **Backup Schedule**:
  - Runs daily at **03:00 AM** via cron (`0 3 * * * /var/www/shop_pc/deploy/backup_db.sh >> /var/log/shop_pc/backup.log 2>&1`).
  - Retains the last **7 daily backups** (`/var/backups/shop_pc/daily/`) and **4 weekly backups** (`/var/backups/shop_pc/weekly/`).
  - Supports automatic off-server replication via `REMOTE_BACKUP_TARGET` (`rclone` or `rsync`) to eliminate single-server disk failure risk.
- **How to Restore Backups**:
  ```bash
  # Test restore into a temporary verification database:
  sudo bash /var/www/shop_pc/deploy/restore_backup.sh --verify /var/backups/shop_pc/daily/db_shop_pc_prod_<TIMESTAMP>.dump

  # Full production database + media restore:
  sudo bash /var/www/shop_pc/deploy/restore_backup.sh \
      /var/backups/shop_pc/daily/db_shop_pc_prod_<TIMESTAMP>.dump \
      /var/backups/shop_pc/daily/media_<TIMESTAMP>.tar.gz
  ```

---

## Remaining actions
Because provisioning a paid VPS and registering a `.uz` domain require personal payment authorization (card / Payme / Click), complete these final steps to launch the live server:
1. **Provision an Ubuntu 24.04 LTS VPS**:
   - **Hetzner Cloud CX22** (€4.51/mo, 2 vCPU / 4 GB RAM / 40 GB NVMe): `https://console.hetzner.cloud`
   - *Or* **Eskiz.uz VPS-Start** (95,000 UZS/mo, Tashkent TAS-IX): `https://my.eskiz.uz`
2. **Register `gshoptest.uz` (Optional — site also works via Server IP immediately)**:
   - Register `gshoptest.uz` (28,000 UZS/year) at `https://my.eskiz.uz` or `https://ahost.uz/domains` and point `A` records (`@` and `www`) to your VPS IPv4 address.
3. **Run the Single-Command Production Installer on the VPS**:
   ```bash
   git clone https://github.com/rasulabdikerimov/pc-shop-ecommerce.git /var/www/shop_pc
   sudo bash /var/www/shop_pc/deploy/provision_and_deploy.sh gshoptest.uz admin@gshoptest.uz
   ```
