# PROJECT AUDIT — PC Shop E-Commerce Modernization

## 1. Executive Summary

This document presents a comprehensive technical, architectural, UI/UX, and security audit of the existing `shop_pc` Django e-commerce repository prior to modernization. The existing codebase is an early-stage prototype containing basic catalog browsing, session-based shopping cart storage, basic authentication, and an incomplete review system.

Our objective is to upgrade `shop_pc` into a complete, production-ready, commercial-grade PC & gaming hardware e-commerce platform while preserving existing database records (`db.sqlite3`), URL compatibility, and core application structure (`config`, `shop`, `cart`).

---

## 2. Existing Architecture & Technical Stack

### 2.1 Directory Structure
```text
shop_pc/
├── cart/                   # Session-based shopping cart app
│   ├── admin.py            # Empty
│   ├── cart.py             # Cart session wrapper class
│   ├── context_processors.py # Exposes `cart` to templates
│   ├── forms.py            # CartAddProductForm (quantity 1..20)
│   ├── models.py           # Empty (no Order/Promo models yet)
│   ├── tests.py            # Empty
│   ├── urls.py             # /cart/, /cart/add/<id>/, /cart/remove/<id>/
│   └── views.py            # cart_detail, cart_add, cart_remove
├── config/                 # Project configuration
│   ├── asgi.py
│   ├── settings.py         # Main configuration
│   ├── urls.py             # Root URL routing
│   └── wsgi.py
├── media/                  # Uploaded media files (Product & User images)
├── shop/                   # Core catalog, user, and review app
│   ├── admin.py            # Basic ModelAdmin registrations
│   ├── forms.py            # UserCreationFormByMe, ReviewForm
│   ├── migrations/         # 0001_initial through 0006_review
│   ├── models.py           # User, Category, Product, Review
│   ├── tests.py            # Empty
│   ├── urls.py             # Catalog, auth, and review routes
│   └── views.py            # Auth, catalog, detail, and review views
├── static/
│   └── css/base.css        # Legacy float-based stylesheet (Ubuntu/Helvetica)
├── templates/
│   ├── cart/detail.html
│   ├── shop/{base,home,detail,add_review}.html
│   └── users/{login,logout,register}.html
├── db.sqlite3              # Existing SQLite database with active records
├── manage.py
└── req.txt                 # Dependencies list
```

### 2.2 Technical Stack & Environment
- **Framework**: Django 4.x (`req.txt` specifies `Django==4.2.7`, `Pillow==10.1.0`, `asgiref==3.7.2`, `sqlparse==0.4.4`, `tzdata==2023.3`).
- **Database**: SQLite3 (`db.sqlite3`) in development; no PostgreSQL or environment variable support configured yet.
- **Existing Data in `db.sqlite3`**:
  - **Users**: 7 users (`admin` superuser, `rasul`, `luffy`, `naruto`, `nara`, `qwerty1`, `qwerty2`).
  - **Categories**: 3 categories (`Headphones`, `Keyboards`, `Monitors`).
  - **Products**: 2 products (`2Egaming 17 pro` at $45.00, `PureWriter TKL RGB` at $70.00) with uploaded images in `media/media/2023/11/07/`.
  - **Reviews**: 0 records.
- **Git Repository**:
  - Branch: `master` tracking `origin/master` (`https://github.com/Rasul0819/shop_pc.git`).
  - History: 5 initial commits ending at `2407e6b` ("rating derlik tayin").

---

## 3. Identified Problems & Bugs

### 3.1 Critical Functional Bugs
1. **Broken Review Submission (`NoReverseMatch`)**:
   - In [`shop/views.py`](file:///d:/Python/django/shop_pc/shop/views.py#L86), `add_review` calls `redirect('product_detail', id=product.id, slug=product.slug)` without the `shop:` namespace, causing a `NoReverseMatch` crash upon review submission.
   - In [`templates/shop/add_review.html`](file:///d:/Python/django/shop_pc/templates/shop/add_review.html#L8-L13), both `{% url 'add_review' product.id %}` and `{% url 'product_detail' product.id product.slug %}` omit the `shop:` namespace, crashing with `NoReverseMatch` on GET rendering as well.
2. **Broken Checkout Button in Cart (`templates/cart/detail.html`)**:
   - Line 58 links the "Checkout" button (`Оформить заказ`) to `{% url 'shop:add_review' product_id=item.product.id %}` outside the `{% for item in cart %}` loop. When the cart is empty, this raises a `NoReverseMatch` error; when non-empty, it sends the user to write a review instead of checking out.
3. **Broken User Registration Form (`shop/forms.py` & `shop/views.py`)**:
   - `UserCreationFormByMe` inherits from `django.contrib.auth.forms.UserCreationForm` (which defines `password1` and `password2`), but `Meta.fields` explicitly includes `'password'` (the raw hashed password field on `AbstractUser`), breaking standard registration form validation.
   - `shop/views.py:register` does not pass `request.FILES` into `UserCreationFormByMe(request.POST, request.FILES)`, so uploaded profile pictures are silently discarded.
   - Email uniqueness is not validated.
4. **Unhandled Invalid Form in `cart_add` (`cart/views.py`)**:
   - If `CartAddProductForm` is invalid, `cart_add` falls through and returns `None`, causing Django to raise `ValueError: The view cart.views.cart_add didn't return an HttpResponse object`.
5. **Invalid HTML Structure in `templates/shop/base.html`**:
   - `<div id="header">` and authentication links are placed inside `<head>...</head>`, and there is no `<body>` tag at all.
   - `<title>Base  </title>` is hardcoded without `{% block title %}{% endblock %}`, ignoring page titles set in child templates.

### 3.2 Missing Features
1. **Order Management & Checkout**: No `Order` or `OrderItem` models, checkout flow, stock deduction, transaction safety, or order statuses (`Pending`, `Confirmed`, `Processing`, `Shipped`, `Delivered`, `Cancelled`).
2. **User Account & Profile System**: No user dashboard, profile view/edit page, password change/reset flow, order history, user review management (edit/delete own reviews), or wishlist.
3. **Catalog Capabilities**: No search, price range filtering, brand filtering, stock tracking, discount pricing, sorting (by price, popularity, newest), or pagination.
4. **Discounts & Promotional Codes**: No product/category discount models or server-validated promo code engine (percentage/fixed discounts, expiration dates, usage limits, minimum order amount).
5. **Custom Administration Dashboard**: No dedicated staff dashboard with KPIs, real-time analytics charts, inventory management, order fulfillment controls, customer management, review moderation, and discount/promo management.
6. **Theme System & Responsive UI**: Legacy float-based CSS (`static/css/base.css`) breaks on mobile/tablet screens and lacks Dark Mode / Light Mode support and custom error pages (`404.html`, `500.html`).
7. **Automated Tests**: `shop/tests.py` and `cart/tests.py` contain zero tests.

---

## 4. Security Issues Identified

1. **Hardcoded Secret Key & Debug Mode**: `SECRET_KEY` and `DEBUG = True` are hardcoded in [`config/settings.py`](file:///d:/Python/django/shop_pc/config/settings.py#L18-L23) with `ALLOWED_HOSTS = []`.
2. **Incomplete `.gitignore`**: `.gitignore` only ignores `venv/`. It fails to exclude `.env`, `__pycache__/`, `*.pyc`, `staticfiles/`, `.pytest_cache/`, etc.
3. **Insecure State-Mutating GET Requests**: `cart_remove` can be triggered via GET links, exposing cart state to CSRF/prefetch issues.
4. **Lack of File Upload Validation**: Image uploads (`User.image`, `Product.image`) do not validate file size or image file extensions.
5. **Missing Production Security Settings**: Missing `CSRF_COOKIE_SECURE`, `SESSION_COOKIE_SECURE`, `SECURE_BROWSER_XSS_FILTER`, `SECURE_CONTENT_TYPE_NOSNIFF`, `SECURE_HSTS_SECONDS`, and `X_FRAME_OPTIONS` configuration for production.
6. **Deprecated Model Meta Option**: `Product.Meta` uses `index_together = (('id', 'slug'), )`, which is deprecated in Django 4.2 in favor of `indexes = [models.Index(fields=['id', 'slug'])]`.

---

## 5. Required Improvements & Modernization Architecture

### 5.1 Database & Model Architecture
We will extend the existing models non-destructively (preserving all existing users, categories, and products in `db.sqlite3`):
- **`shop.User`** (extends `AbstractUser`): Preserve `image` and `phone_num`; add `address`, `city`, `postal_code`, `bio`, and helper methods/properties for profile avatar URL, total orders, and total reviews.
- **`shop.Category`**: Add `description`, `icon` (optional), `is_active`, `created_at`.
- **`shop.Brand`**: New model (`name`, `slug`, `description`, `logo`, `is_active`).
- **`shop.Product`**: Preserve existing fields (`category`, `name`, `slug`, `image`, `description`, `price`, `available`, `created`, `uploaded`); add `brand` (FK to `Brand`, nullable), `original_price` (DecimalField, nullable), `stock` (PositiveIntegerField, default=10), `sku` (CharField, blank=True), `specifications` (JSONField/TextField, blank=True), `is_featured` (BooleanField, default=False), `sales_count` (PositiveIntegerField, default=0). Add dynamic discount calculation properties (`get_effective_price`, `get_discount_percentage`, `has_discount`, `in_stock`, `average_rating`, `review_count`).
- **`shop.ProductImage`**: Additional gallery images per product (`product`, `image`, `alt_text`, `is_primary`).
- **`shop.Review`**: Preserve existing fields (`product`, `user`, `title`, `body`, `rating`, `created_at`); add `updated_at` and `is_approved` (default=True).
- **`shop.Wishlist`**: User wishlist (`user`, `product`, `created_at` with ` unique_together = ('user', 'product')`).
- **`shop.Discount`**: Campaign/product/category discount model (`name`, `description`, `discount_type` [percentage/fixed], `value`, `products` M2M, `categories` M2M, `start_date`, `end_date`, `is_active`, `created_at`).
- **`cart.PromoCode`**: Promotional code engine (`code`, `description`, `discount_type` [percentage/fixed], `discount_value`, `min_order_amount`, `max_uses`, `used_count`, `valid_from`, `valid_until`, `is_active`, `created_at`).
- **`cart.Order` & `cart.OrderItem`**: Complete order management system with unique `order_number`, customer contact & shipping details, `status` (`pending`, `confirmed`, `processing`, `shipped`, `delivered`, `cancelled`), `payment_status` (`pending`, `paid`, `failed`, `refunded`), `payment_method`, `subtotal`, `discount_amount`, `promo_code` FK, `total_amount`, timestamps, and line items storing historical unit price and quantity.
- **`shop.AdminAuditLog`**: Records sensitive staff operations in the custom administration panel.

### 5.2 Implementation Roadmap
1. **Phase 1 — Audit**: Complete `PROJECT_AUDIT.md` and commit.
2. **Phase 2 — Project Configuration & Security Foundation**: Environment-based `settings.py` (`python-dotenv`), `.env.example`, expanded `.gitignore`, custom 404/500 handlers, security headers, PostgreSQL + SQLite support.
3. **Phase 3 — Database Models & Migrations**: Extend `shop` and `cart` models for Brands, Products (stock, original price, specs), Discounts, PromoCodes, Wishlist, Orders, OrderItems, and AdminAuditLog. Run migrations and seed rich PC hardware catalog data while keeping existing products intact.
4. **Phase 4 — Base Layout, Design System & Light/Dark Theme Engine**: Modern commercial e-commerce design system using CSS variables, FOUC-free theme initialization, responsive header/mega-nav/footer, toast notifications, and custom 404/500 pages.
5. **Phase 5 — Homepage, Product Catalog, Search, Filtering, Sorting & Product Details**: Redesigned homepage (hero, featured deals, category showcase), full catalog filter/sort/pagination engine, rich product details page with specs, gallery, discount badges, stock status, and verified reviews.
6. **Phase 6 — Authentication, User Profiles, Wishlist & Review Management**: Registration with file upload & unique email validation, login, POST logout, password reset/change flows, user dashboard, profile editor, wishlist toggles, purchase history, order detail view, and user review editor/deleter with strict ownership checks.
7. **Phase 7 — Shopping Cart, Promo Codes & Transactional Order Checkout**: Enhanced server-validated cart with stock verification, promo code application/removal, active discount calculations, and atomic `transaction.atomic()` `select_for_update()` checkout flow with order confirmation.
8. **Phase 8 — Custom Administration Dashboard & Analytics**: Dedicated `/dashboard/` staff portal with KPI cards, real database charts (revenue over time, orders over time, category performance, best sellers, customer registrations, discount usage), and full CRUD management for Products, Categories, Brands, Orders, Customers, Reviews, Discounts, and Promo Codes.
9. **Phase 9 — Comprehensive Automated & Browser Testing**: 30+ unit and integration tests covering all 26 required areas + Playwright headless browser verification across desktop and mobile viewports and Light/Dark modes.
10. **Phase 10 — Production Deployment Configuration & Final Documentation**: Production configs (`gunicorn`, `nginx`, `systemd`, PostgreSQL setup, backup scripts, `.uz` domain & VPS analysis), `DEPLOYMENT.md`, and `FINAL_REPORT.md`.

