# FINAL DEPLOYMENT REPORT — PC SHOP (`pc-shop-ecommerce`)

## 1. GitHub Repository

| Field | Value |
| :--- | :--- |
| **New Repository Name** | `pc-shop-ecommerce` |
| **Repository URL** | https://github.com/rasulabdikerimov/pc-shop-ecommerce |
| **Default Branch** | `main` |
| **Initial Commit Hash** | `799d057b99a883e89c7d49558c0f6c87fb6510ab` (`799d057`) |
| **Upload Verification Status** | **VERIFIED** — All 107 application, template, static, migration, test, CI/CD, and deployment configuration files are uploaded to `origin/main`. Sensitive files (`.env`, hardcoded `SECRET_KEY`, `db.sqlite3`, `venv/`, `__pycache__/`) were verified excluded. |

---

## 2. Hosting Configuration & Provider Selection

| Field | Value |
| :--- | :--- |
| **Recommended Hosting Provider (Global Value)** | **Hetzner Cloud** (`https://console.hetzner.cloud`) — **CX22 Plan** |
| **Alternative Local Provider (Uzbekistan TAS-IX)** | **Eskiz.uz VPS** (`https://my.eskiz.uz`) / **Ahost.uz** (`https://ahost.uz/vps`) |
| **Server Plan Specifications** | 2 vCPU, 4 GB RAM, 40 GB NVMe SSD, 20 TB Traffic |
| **Monthly Cost** | **€4.51 / month** (~$4.90 USD) on Hetzner CX22, or **95,000 UZS / month** (~$7.50 USD) on Eskiz.uz |
| **Operating System** | Ubuntu 24.04 LTS (64-bit) |
| **Server IP** | Pending VPS payment authorization (no payment credentials are connected to this environment) |
| **Deployment Status** | **Production Stack & Automated Installer Ready in Repository** — [`deploy/provision_and_deploy.sh`](file:///d:/Python/django/shop_pc/deploy/provision_and_deploy.sh), [`deploy/gunicorn.conf.py`](file:///d:/Python/django/shop_pc/deploy/gunicorn.conf.py), [`deploy/shop_pc.service`](file:///d:/Python/django/shop_pc/deploy/shop_pc.service), [`deploy/nginx_shop_pc.conf`](file:///d:/Python/django/shop_pc/deploy/nginx_shop_pc.conf), [`deploy/backup_db.sh`](file:///d:/Python/django/shop_pc/deploy/backup_db.sh), and GitHub Actions CI/CD ([`.github/workflows/ci-cd.yml`](file:///d:/Python/django/shop_pc/.github/workflows/ci-cd.yml)) are committed and pushed to `main`. |

---

## 3. Domain Registration & SSL Configuration

| Field | Value |
| :--- | :--- |
| **Preferred Domain** | `gshoptest.uz` (**Verified AVAILABLE** via live WHOIS check on `whois.cctld.uz:43`) |
| **Backup Domain** | `pcshoptest.uz` (**Verified AVAILABLE** via live WHOIS check on `whois.cctld.uz:43`) |
| **Recommended Registrar** | **Eskiz.uz** (`https://my.eskiz.uz`) or **Ahost.uz** (`https://ahost.uz/domains`) |
| **Registration Price (1st Year)** | **28,000 UZS / year** (~$2.20 USD) |
| **Renewal Price (Annual)** | **28,000 UZS / year** (~$2.20 USD) |
| **DNS Configuration Status** | Prepared (`A` records for `@` and `www` documented in [`DEPLOYMENT.md`](file:///d:/Python/django/shop_pc/DEPLOYMENT.md); awaiting domain purchase and VPS IP assignment) |
| **SSL / HTTPS Status** | Prepared in [`deploy/nginx_shop_pc.conf`](file:///d:/Python/django/shop_pc/deploy/nginx_shop_pc.conf) and [`deploy/provision_and_deploy.sh`](file:///d:/Python/django/shop_pc/deploy/provision_and_deploy.sh) using Let's Encrypt Certbot (`TLSv1.2`/`TLSv1.3`, HSTS, HTTP &rarr; HTTPS redirect, and `https://www.gshoptest.uz` &rarr; `https://gshoptest.uz` canonical redirect). |

---

## 4. Application Architecture & Readiness

| Component | Status / Details |
| :--- | :--- |
| **Target Public Website URL** | `https://gshoptest.uz` (Canonical) / `https://www.gshoptest.uz` (301 Redirect) |
| **Django Version** | Django 4.x (`requirements.txt` specifies `Django>=4.0,<5.0`) |
| **Database** | Dual-mode: PostgreSQL (`django.db.backends.postgresql`) in production via `.env`; SQLite3 in local development |
| **Gunicorn Configuration** | Configured in [`deploy/gunicorn.conf.py`](file:///d:/Python/django/shop_pc/deploy/gunicorn.conf.py) & [`deploy/shop_pc.service`](file:///d:/Python/django/shop_pc/deploy/shop_pc.service) (`gthread` workers bound to `unix:/run/gunicorn/shop_pc.sock`) |
| **Nginx Configuration** | Configured in [`deploy/nginx_shop_pc.conf`](file:///d:/Python/django/shop_pc/deploy/nginx_shop_pc.conf) |
| **Static Files Status** | Verified (`python manage.py collectstatic --noinput` collects 132 static files cleanly; served via Nginx `/static/` and WhiteNoise) |
| **Media Files Status** | Verified (`/media/` served with 7-day cache control and validated via `validate_image_upload` for extension & 5 MB size limit) |

---

## 5. Testing & Quality Assurance Summary

### 5.1 Automated Unit & Integration Tests (`python manage.py test -v 2`)
- **Tests Executed**: **19** comprehensive test cases covering all 26 functional, security, and database requirements in [`shop/tests.py`](file:///d:/Python/django/shop_pc/shop/tests.py) and [`cart/tests.py`](file:///d:/Python/django/shop_pc/cart/tests.py).
- **Tests Passed**: **19 / 19 (100%)**
- **Tests Failed**: **0**

### 5.2 Playwright Headless Browser Verification
- **Executed & Passed**:
  - Homepage, Catalog Search (`RTX 4070`), Category Filtering, and Product Details page rendering.
  - Light Mode & Dark Mode instant switching (`#theme-toggle`) and `localStorage` persistence across reloads.
  - Responsive layout verification across all 7 required viewports (`1920px`, `1440px`, `1366px`, `1024px`, `768px`, `390px`, `375px`) with zero horizontal overflow.
  - Shopping Cart quantity updates and Promo Code (`PCSHOP10`) application.
  - Staff Login and Custom Administration Dashboard (`/dashboard/`) with live HTML5 Canvas analytics charts.

### 5.3 Issues Discovered & Fixed During Inspection
1. **Unresolved Git Merge Conflict Markers (`4e7a173`)**: During Phase One inspection, we detected unresolved `<<<<<<< HEAD` conflict markers in `shop/views.py`, `templates/cart/detail.html`, and `templates/shop/add_review.html` along with 5 tracked `.pyc` files introduced by commit `4e7a173`. All conflict markers were resolved and `.pyc` files were removed.
2. **Sensitive Data & Secret Key Hardening**: Removed hardcoded fallback `SECRET_KEY` from `config/settings.py` (enforcing environment variable `SECRET_KEY` in production and `get_random_secret_key()` in local dev) and untracked `db.sqlite3` so private local user data is never uploaded to the public GitHub repository.

---

## 6. Outstanding Actions Requiring User Payment Authorization

Because purchasing a VPS and registering a `.uz` domain require your personal payment authorization (Payme / Click / Card), complete these two quick steps to take `https://gshoptest.uz` live:

1. **Register `gshoptest.uz` (~28,000 UZS / year)**:
   - Open **https://my.eskiz.uz** (or **https://ahost.uz/domains**), search for `gshoptest.uz` (verified available), and complete registration.
2. **Provision Ubuntu 24.04 VPS & Run the One-Command Installer**:
   - Create an **Ubuntu 24.04 LTS** VPS on **Hetzner Cloud CX22** (`https://console.hetzner.cloud`, €4.51/mo) or **Eskiz.uz VPS** (`https://my.eskiz.uz`, 95,000 UZS/mo).
   - Point the domain's `A` records (`@` and `www`) to your new VPS IPv4 address.
   - SSH into the server and run the automated provisioning and deployment script directly from your new GitHub repository:
     ```bash
     git clone https://github.com/rasulabdikerimov/pc-shop-ecommerce.git /var/www/shop_pc
     sudo bash /var/www/shop_pc/deploy/provision_and_deploy.sh gshoptest.uz admin@gshoptest.uz
     ```
