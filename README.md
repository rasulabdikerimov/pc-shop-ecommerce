# PC Shop — Modern E-Commerce Platform for PC Hardware & Gaming Gear

[![Django CI](https://img.shields.io/badge/Django-4.x-092E20?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Ready-336791?logo=postgresql&logoColor=white)](https://www.postgresql.org/)

**PC Shop** (`pc-shop-ecommerce`) is a full-featured, production-ready commercial e-commerce web application built with Django. It provides a responsive storefront for custom PC builders and gamers, a complete Light/Dark theme engine, server-validated promotional codes and discount campaigns, transactional checkout with stock locking, customer account dashboards, and a dedicated custom staff administration & analytics portal.

---

## Main Features

### Storefront & Catalog
- **Dynamic Hardware Catalog**: Browse graphics cards, processors, gaming monitors, mechanical keyboards, headsets, mice, and NVMe SSDs.
- **Advanced Filtering & Sorting**: Combine keyword search (`?q=`), category filtering, brand filtering, min/max price range, in-stock filter, active discount filter, multi-criteria sorting (`newest`, `popular`, `price_asc`, `price_desc`, `name_asc`), and pagination.
- **Rich Product Details**: High-resolution imagery, technical specifications table, live stock availability badges, discount savings calculation, related hardware recommendations, and verified customer reviews.
- **Instant Light Mode & Dark Mode**: FOUC-free theme switching with Sun/Moon header toggle, `localStorage` persistence (`pcshop_theme`), and OS `prefers-color-scheme` detection.

### Customer Accounts & Personalization
- **Secure Authentication**: Registration with avatar upload and unique email/username validation, login, logout, password change, and email-based password recovery.
- **Personal Account Dashboard (`/account/`)**: Lifetime spending & order counters, profile settings editor, full purchase history with individual order receipts, review management (edit/delete own reviews), and saved Wishlist.
- **Strict Ownership Security**: Customers can only access their own orders and modify their own reviews.

### Shopping Cart, Discounts & Transactional Checkout
- **Server-Side Financial Engine**: All item prices, product/category campaign discounts, and promotional code reductions are calculated on the server using `Decimal` arithmetic.
- **Promotional Code Validation**: Supports percentage and fixed-amount promo codes with start/expiration dates, minimum order thresholds, and usage limits while preventing negative order totals.
- **Race-Condition-Free Checkout**: Uses `transaction.atomic()` and `select_for_update()` row locking to verify and deduct stock atomically when creating orders.

### Custom Administration Dashboard (`/dashboard/`)
- **Executive KPIs & Real Database Analytics**: 8 KPI summary cards and 6 interactive HTML5 Canvas charts (Revenue Over Time, Orders Over Time, Best-Selling Products, Category Performance, Customer Registrations, Promo Code Usage).
- **Full Store Management**: Dedicated staff interfaces for managing Products & Inventory, Categories & Brands, Order Fulfillment & Payment Statuses, Customer Accounts, Review Moderation, and Discount Campaigns / Promo Codes, backed by an administrative audit log (`AdminAuditLog`).

---

## Technology Stack

- **Backend**: Python 3.10+, Django 4.x (`django.contrib.auth`, ORM, Transactions, Class/Function Views)
- **Database**: PostgreSQL (Production) / SQLite3 (Local Development)
- **Frontend**: Semantic HTML5, Modern CSS3 Custom Properties (Light/Dark Theme Engine, CSS Grid/Flexbox), Vanilla ES6 JavaScript, HTML5 Canvas Charts
- **Image Processing**: Pillow (`PIL`)
- **Production Server Stack**: Ubuntu LTS, Gunicorn (`gthread` workers), systemd, Nginx (Reverse Proxy + Static/Media serving), WhiteNoise, Let's Encrypt Certbot (TLS 1.2/1.3)
- **Testing & CI/CD**: Django `TestCase` Suite, Playwright Chromium Headless E2E Verification, GitHub Actions CI/CD (`.github/workflows/ci-cd.yml`)

---

## Local Development Setup

### 1. Clone the Repository
```bash
git clone https://github.com/rasulabdikerimov/pc-shop-ecommerce.git
cd pc-shop-ecommerce
```

### 2. Create and Activate a Virtual Environment
```bash
# Linux / macOS
python3 -m venv venv
source venv/bin/activate

# Windows (PowerShell)
py -3.10 -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env` for local development:
```bash
cp .env.example .env
```
For local SQLite development, set in `.env`:
```ini
DEBUG=True
SECRET_KEY=your-local-development-secret-key
ALLOWED_HOSTS=localhost,127.0.0.1,testserver
DB_ENGINE=sqlite3
```

### 5. Run Migrations & Seed Sample Hardware Catalog
```bash
python manage.py migrate
python manage.py seed_catalog
python manage.py collectstatic --noinput
```

### 6. Create an Administrative Superuser (Optional)
```bash
python manage.py createsuperuser
```

### 7. Start the Development Server
```bash
python manage.py runserver
```
- **Storefront**: `http://127.0.0.1:8000/`
- **Custom Admin Dashboard**: `http://127.0.0.1:8000/dashboard/`
- **Native Django Admin**: `http://127.0.0.1:8000/admin/`

---

## Running Automated Tests

Execute the full automated test suite (19 test methods covering catalog, search, filtering, sorting, auth, profile, wishlist, reviews, discounts, promo codes, cart, transactional checkout, permissions, custom admin, and migrations):
```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test -v 2
```

---

## Production Deployment Overview

Complete production configuration files are located in the [`deploy/`](file:///d:/Python/django/shop_pc/deploy) directory:
- [`deploy/provision_and_deploy.sh`](file:///d:/Python/django/shop_pc/deploy/provision_and_deploy.sh) — Automated 12-step Ubuntu LTS server provisioning, hardening, and deployment installer
- [`deploy/gunicorn.conf.py`](file:///d:/Python/django/shop_pc/deploy/gunicorn.conf.py) — Gunicorn WSGI server configuration
- [`deploy/shop_pc.service`](file:///d:/Python/django/shop_pc/deploy/shop_pc.service) — systemd service unit for automatic process management
- [`deploy/nginx_shop_pc.conf`](file:///d:/Python/django/shop_pc/deploy/nginx_shop_pc.conf) — Nginx reverse proxy, Gzip, canonical domain redirect, and SSL configuration
- [`deploy/backup_db.sh`](file:///d:/Python/django/shop_pc/deploy/backup_db.sh) — Automated daily (7-day) & weekly (4-week) PostgreSQL and media backup script with off-server sync support
- [`deploy/restore_backup.sh`](file:///d:/Python/django/shop_pc/deploy/restore_backup.sh) — Backup verification and production database/media restoration script
- [`deploy/migrate_sqlite_to_postgres.sh`](file:///d:/Python/django/shop_pc/deploy/migrate_sqlite_to_postgres.sh) — Non-destructive SQLite to PostgreSQL data migration script

See [**DEPLOYMENT.md**](file:///d:/Python/django/shop_pc/DEPLOYMENT.md) for the complete step-by-step production deployment, domain setup, SSL configuration, and maintenance guide.
