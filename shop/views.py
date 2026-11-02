from decimal import Decimal, InvalidOperation
from functools import wraps
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.db.models.functions import TruncDate
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.utils.http import urlencode

from .models import (
    User, Category, Brand, Product, Discount, Review, Wishlist, AdminAuditLog
)
from .forms import (
    UserCreationFormByMe, UserProfileForm, ReviewForm,
    AdminProductForm, AdminCategoryForm, AdminBrandForm,
    AdminDiscountForm, AdminPromoCodeForm, AdminOrderUpdateForm
)
from cart.forms import CartAddProductForm
from cart.models import PromoCode, Order, OrderItem


def staff_required(view_func):
    """Decorator ensuring only authenticated staff members can access custom admin views."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"/login/?next={request.path}")
        if not request.user.is_staff:
            raise PermissionDenied("You do not have staff permissions to access the administration panel.")
        return view_func(request, *args, **kwargs)
    return _wrapped


def log_admin_action(user, action, target_model, target_id='', details=''):
    """Helper to record administrative operations in AdminAuditLog."""
    try:
        AdminAuditLog.objects.create(
            user=user if user and user.is_authenticated else None,
            action=action,
            target_model=target_model,
            target_id=str(target_id),
            details=details
        )
    except Exception:
        pass


# ==============================================================================
# AUTHENTICATION VIEWS
# ==============================================================================

def loginuser(request):
    if request.method == 'POST':
        username = (request.POST.get('username') or '').strip()
        password = request.POST.get('password') or ''
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url and next_url.startswith('/'):
                return redirect(next_url)
            return redirect('shop:product_list')
        else:
            return render(request, 'users/login.html', {'error': 'Invalid username or password.'})
    return render(request, 'users/login.html')


def logoutuser(request):
    logout(request)
    messages.info(request, "You have been signed out.")
    return redirect('shop:product_list')


def register(request):
    if request.method == 'POST':
        form = UserCreationFormByMe(request.POST, request.FILES)
        if form.is_valid():
            new_user = form.save()
            login(request, new_user)
            messages.success(request, f"Account was created for {new_user.username}!")
            return redirect('shop:product_list')
        else:
            messages.error(request, "Please correct the highlighted errors below.")
            return render(request, 'users/register.html', {'form': form})
    else:
        form = UserCreationFormByMe()
    return render(request, 'users/register.html', {'form': form})


# ==============================================================================
# STOREFRONT & CATALOG VIEWS
# ==============================================================================

def product_list(request, category_slug=None, template_name='shop/home.html'):
    category = None
    categories = Category.objects.filter(is_active=True).annotate(
        product_count=Count('products', filter=Q(products__available=True))
    )
    brands = Brand.objects.filter(is_active=True)
    products_qs = (
        Product.objects.filter(available=True)
        .select_related('category', 'brand')
        .prefetch_related('discounts', 'category__discounts', 'reviews')
    )
    total_catalog_count = products_qs.count()

    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products_qs = products_qs.filter(category=category)

    # Search query
    search_query = (request.GET.get('q') or '').strip()
    if search_query:
        products_qs = products_qs.filter(
            Q(name__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(short_specs__icontains=search_query)
            | Q(sku__icontains=search_query)
            | Q(brand__name__icontains=search_query)
            | Q(category__name__icontains=search_query)
        )

    # Brand filter
    selected_brand = (request.GET.get('brand') or '').strip()
    if selected_brand:
        products_qs = products_qs.filter(brand__slug=selected_brand)

    # Price filters
    min_price_raw = (request.GET.get('min_price') or '').strip()
    max_price_raw = (request.GET.get('max_price') or '').strip()
    min_price_val = None
    max_price_val = None
    if min_price_raw:
        try:
            min_price_val = Decimal(min_price_raw)
            products_qs = products_qs.filter(price__gte=min_price_val)
        except InvalidOperation:
            min_price_raw = ''
    if max_price_raw:
        try:
            max_price_val = Decimal(max_price_raw)
            products_qs = products_qs.filter(price__lte=max_price_val)
        except InvalidOperation:
            max_price_raw = ''

    # Availability filter
    in_stock_only = request.GET.get('in_stock') == '1'
    if in_stock_only:
        products_qs = products_qs.filter(stock__gt=0)

    # On-sale / discount filter
    on_sale_only = request.GET.get('on_sale') == '1'
    if on_sale_only:
        now = timezone.now()
        products_qs = products_qs.filter(
            Q(original_price__gt=0)
            | Q(discount_percent__gt=0)
            | Q(discounts__is_active=True, discounts__start_date__lte=now)
            | Q(category__discounts__is_active=True, category__discounts__start_date__lte=now)
        ).distinct()

    # Sorting
    current_sort = (request.GET.get('sort') or 'newest').strip()
    if current_sort == 'price_asc':
        products_qs = products_qs.order_by('price', 'name')
    elif current_sort == 'price_desc':
        products_qs = products_qs.order_by('-price', 'name')
    elif current_sort == 'popular':
        products_qs = products_qs.order_by('-sales_count', '-created')
    elif current_sort == 'name_asc':
        products_qs = products_qs.order_by('name')
    else:
        current_sort = 'newest'
        products_qs = products_qs.order_by('-created', '-id')

    total_filtered_count = products_qs.count()

    # Pagination
    paginator = Paginator(products_qs, 8)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Build clean filter querystring for pagination links
    query_params = {}
    if search_query:
        query_params['q'] = search_query
    if selected_brand:
        query_params['brand'] = selected_brand
    if min_price_raw:
        query_params['min_price'] = min_price_raw
    if max_price_raw:
        query_params['max_price'] = max_price_raw
    if in_stock_only:
        query_params['in_stock'] = '1'
    if on_sale_only:
        query_params['on_sale'] = '1'
    if current_sort and current_sort != 'newest':
        query_params['sort'] = current_sort
    filter_querystring = urlencode(query_params)

    has_active_filters = bool(
        selected_brand or min_price_raw or max_price_raw or in_stock_only or on_sale_only
    )

    now = timezone.now()
    active_discounts = Discount.objects.filter(
        is_active=True, start_date__lte=now
    ).filter(Q(end_date__isnull=True) | Q(end_date__gte=now))[:3]

    featured_products = Product.objects.filter(available=True, is_featured=True).select_related('category', 'brand')[:4]

    return render(
        request,
        template_name,
        {
            'category': category,
            'categories': categories,
            'brands': brands,
            'products': page_obj.object_list,
            'page_obj': page_obj,
            'total_catalog_count': total_catalog_count,
            'total_filtered_count': total_filtered_count,
            'search_query': search_query,
            'selected_brand': selected_brand,
            'min_price': min_price_raw,
            'max_price': max_price_raw,
            'in_stock_only': in_stock_only,
            'on_sale_only': on_sale_only,
            'current_sort': current_sort,
            'filter_querystring': filter_querystring,
            'has_active_filters': has_active_filters,
            'active_discounts': active_discounts,
            'featured_products': featured_products,
        }
    )


def catalog_view(request):
    return product_list(request, category_slug=None, template_name='shop/catalog.html')


def product_detail(request, id, slug):
    product = get_object_or_404(
        Product.objects.select_related('category', 'brand'),
        id=id,
        slug=slug,
        available=True
    )
    reviews = Review.objects.filter(product=product, is_approved=True).select_related('user')
    cart_product_form = CartAddProductForm()
    related_products = (
        Product.objects.filter(category=product.category, available=True)
        .exclude(id=product.id)
        .select_related('category', 'brand')[:4]
    )
    in_wishlist = False
    if request.user.is_authenticated:
        in_wishlist = Wishlist.objects.filter(user=request.user, product=product).exists()

    return render(
        request,
        'shop/detail.html',
        {
            'product': product,
            'cart_product_form': cart_product_form,
            'reviews': reviews,
            'related_products': related_products,
            'in_wishlist': in_wishlist,
        }
    )


# ==============================================================================
# CUSTOMER REVIEWS (WITH STRICT OWNERSHIP PROTECTION)
# ==============================================================================

@login_required
def add_review(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.user = request.user
            review.save()
            messages.success(request, "Thank you! Your review has been published.")
            return redirect('shop:product_detail', id=product.id, slug=product.slug)
    else:
        form = ReviewForm()

    return render(request, 'shop/add_review.html', {'form': form, 'product': product})


@login_required
def edit_review(request, review_id):
    review = get_object_or_404(Review, id=review_id, user=request.user)
    if request.method == 'POST':
        form = ReviewForm(request.POST, instance=review)
        if form.is_valid():
            form.save()
            messages.success(request, "Your review has been updated.")
            return redirect('shop:product_detail', id=review.product.id, slug=review.product.slug)
    else:
        form = ReviewForm(instance=review)
    return render(request, 'shop/edit_review.html', {'form': form, 'review': review})


@login_required
@require_POST
def delete_review(request, review_id):
    review = get_object_or_404(Review, id=review_id, user=request.user)
    product = review.product
    review.delete()
    messages.info(request, "Your review has been deleted.")
    next_url = request.POST.get('next')
    if next_url and next_url.startswith('/'):
        return redirect(next_url)
    return redirect('shop:product_detail', id=product.id, slug=product.slug)


# ==============================================================================
# USER ACCOUNT, PROFILE, ORDERS, REVIEWS & WISHLIST VIEWS
# ==============================================================================

@login_required
def user_dashboard(request):
    user_orders = Order.objects.filter(user=request.user).prefetch_related('items')
    user_reviews_qs = Review.objects.filter(user=request.user).select_related('product')
    wishlist_items_count = Wishlist.objects.filter(user=request.user).count()

    return render(
        request,
        'users/dashboard.html',
        {
            'total_orders': user_orders.count(),
            'total_spent': request.user.total_spent,
            'total_reviews': user_reviews_qs.count(),
            'wishlist_items_count': wishlist_items_count,
            'recent_orders': user_orders[:5],
            'recent_reviews': user_reviews_qs[:5],
        }
    )


@login_required
def profile_edit(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been updated successfully.")
            return redirect('shop:user_dashboard')
        else:
            messages.error(request, "Please fix the errors highlighted below.")
    else:
        form = UserProfileForm(instance=request.user)
    return render(request, 'users/profile_edit.html', {'form': form})


@login_required
def password_change_view(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Your password was updated successfully.")
            return redirect('shop:user_dashboard')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'users/password_change.html', {'form': form})


@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).prefetch_related('items__product')
    return render(request, 'users/order_history.html', {'orders': orders})


@login_required
def user_order_detail(request, order_number):
    # Strictly enforce that customers can only view their own orders
    order = get_object_or_404(
        Order.objects.prefetch_related('items__product'),
        order_number=order_number,
        user=request.user
    )
    return render(request, 'users/order_detail.html', {'order': order})


@login_required
def user_reviews(request):
    reviews = Review.objects.filter(user=request.user).select_related('product')
    return render(request, 'users/user_reviews.html', {'reviews': reviews})


@login_required
def wishlist_view(request):
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related(
        'product__category', 'product__brand'
    )
    return render(request, 'users/wishlist.html', {'wishlist_items': wishlist_items})


@login_required
@require_POST
def wishlist_toggle(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    item, created = Wishlist.objects.get_or_create(user=request.user, product=product)
    if not created:
        item.delete()
        messages.info(request, f"Removed '{product.name}' from your wishlist.")
    else:
        messages.success(request, f"Added '{product.name}' to your wishlist.")

    next_url = request.POST.get('next')
    if next_url and next_url.startswith('/'):
        return redirect(next_url)
    return redirect('shop:wishlist')


# ==============================================================================
# CUSTOM ADMINISTRATION PANEL (/dashboard/...)
# ==============================================================================

@staff_required
def admin_dashboard(request):
    now = timezone.now()
    valid_orders = Order.objects.exclude(status='cancelled')
    total_revenue = valid_orders.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    total_orders = Order.objects.count()
    pending_orders = Order.objects.filter(status='pending').count()
    completed_orders = Order.objects.filter(status='delivered').count()
    total_customers = User.objects.count()
    total_products = Product.objects.count()
    total_reviews = Review.objects.count()
    active_discounts_count = Discount.objects.filter(is_active=True).count()
    active_promos_count = PromoCode.objects.filter(is_active=True).count()

    recent_orders = Order.objects.select_related('user')[:6]
    recent_customers = User.objects.order_by('-date_joined')[:6]
    best_selling_products = Product.objects.select_related('category', 'brand').order_by('-sales_count', '-id')[:6]
    audit_logs = AdminAuditLog.objects.select_related('user')[:6]

    # Build real database chart series
    # 1 & 2: Revenue & Orders by Date
    daily_orders = (
        valid_orders
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(rev=Sum('total_amount'), cnt=Count('id'))
        .order_by('day')
    )
    rev_labels = [entry['day'].strftime('%b %d') if entry['day'] else 'Today' for entry in daily_orders] or ['Current']
    rev_values = [float(entry['rev'] or 0) for entry in daily_orders] or [float(total_revenue)]
    ord_values = [int(entry['cnt'] or 0) for entry in daily_orders] or [total_orders]

    # 3: Best-selling products
    bs_labels = [p.name[:14] for p in best_selling_products]
    bs_values = [int(p.sales_count) for p in best_selling_products]

    # 4: Category performance (revenue from OrderItem or catalog value)
    cat_stats = (
        Category.objects.annotate(
            cat_rev=Sum('products__order_items__price'),
            cat_sales=Sum('products__sales_count')
        )
        .order_by('-cat_sales')[:6]
    )
    cat_labels = [c.name[:12] for c in cat_stats]
    cat_values = [float(c.cat_rev or (c.cat_sales or 0) * 45) for c in cat_stats]

    # 5: Customer registrations by date
    reg_stats = (
        User.objects.annotate(day=TruncDate('date_joined'))
        .values('day')
        .annotate(cnt=Count('id'))
        .order_by('day')
    )
    reg_labels = [r['day'].strftime('%b %d') if r['day'] else 'Joined' for r in reg_stats] or ['Total']
    reg_values = [int(r['cnt']) for r in reg_stats] or [total_customers]

    # 6: Promo code usage
    promos_qs = PromoCode.objects.all()[:6]
    promo_labels = [p.code for p in promos_qs] or ['NONE']
    promo_values = [int(p.used_count) for p in promos_qs] or [0]

    chart_data_json = {
        'revenue': {'labels': rev_labels, 'values': rev_values},
        'orders': {'labels': rev_labels, 'values': ord_values},
        'bestsellers': {'labels': bs_labels, 'values': bs_values},
        'categories': {'labels': cat_labels, 'values': cat_values},
        'registrations': {'labels': reg_labels, 'values': reg_values},
        'promos': {'labels': promo_labels, 'values': promo_values},
    }

    return render(
        request,
        'admin_panel/dashboard.html',
        {
            'admin_section': 'dashboard',
            'total_revenue': total_revenue,
            'total_orders': total_orders,
            'pending_orders': pending_orders,
            'completed_orders': completed_orders,
            'total_customers': total_customers,
            'total_products': total_products,
            'total_reviews': total_reviews,
            'active_discounts_count': active_discounts_count,
            'active_promos_count': active_promos_count,
            'recent_orders': recent_orders,
            'recent_customers': recent_customers,
            'best_selling_products': best_selling_products,
            'audit_logs': audit_logs,
            'chart_data_json': chart_data_json,
        }
    )


@staff_required
def admin_products(request):
    products = Product.objects.select_related('category', 'brand').order_by('-id')
    search_q = (request.GET.get('q') or '').strip()
    selected_cat = (request.GET.get('category') or '').strip()
    if search_q:
        products = products.filter(Q(name__icontains=search_q) | Q(sku__icontains=search_q))
    if selected_cat:
        products = products.filter(category__slug=selected_cat)

    return render(
        request,
        'admin_panel/products.html',
        {
            'admin_section': 'products',
            'products': products,
            'categories': Category.objects.all(),
            'search_q': search_q,
            'selected_cat': selected_cat,
        }
    )


@staff_required
def admin_product_add(request):
    if request.method == 'POST':
        form = AdminProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            log_admin_action(request.user, f"Created product '{product.name}'", 'Product', product.id)
            messages.success(request, f"Product '{product.name}' was created successfully.")
            return redirect('shop:admin_products')
    else:
        form = AdminProductForm()
    return render(
        request,
        'admin_panel/product_form.html',
        {'admin_section': 'products', 'form': form, 'is_edit': False}
    )


@staff_required
def admin_product_edit(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        form = AdminProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            product = form.save()
            log_admin_action(request.user, f"Updated product '{product.name}'", 'Product', product.id)
            messages.success(request, f"Product '{product.name}' updated.")
            return redirect('shop:admin_products')
    else:
        form = AdminProductForm(instance=product)
    return render(
        request,
        'admin_panel/product_form.html',
        {'admin_section': 'products', 'form': form, 'product': product, 'is_edit': True}
    )


@staff_required
@require_POST
def admin_product_toggle(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.available = not product.available
    product.save(update_fields=['available'])
    state_str = 'visible' if product.available else 'hidden'
    log_admin_action(request.user, f"Set product '{product.name}' {state_str}", 'Product', product.id)
    messages.info(request, f"Product '{product.name}' is now {state_str}.")
    return redirect('shop:admin_products')


@staff_required
@require_POST
def admin_product_delete(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    name = product.name
    product.delete()
    log_admin_action(request.user, f"Deleted product '{name}'", 'Product', product_id)
    messages.info(request, f"Deleted product '{name}'.")
    return redirect('shop:admin_products')


@staff_required
def admin_categories_brands(request):
    category_form = AdminCategoryForm()
    brand_form = AdminBrandForm()

    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        if form_type == 'category':
            category_form = AdminCategoryForm(request.POST)
            if category_form.is_valid():
                cat = category_form.save()
                log_admin_action(request.user, f"Created category '{cat.name}'", 'Category', cat.id)
                messages.success(request, f"Category '{cat.name}' added.")
                return redirect('shop:admin_categories_brands')
        elif form_type == 'brand':
            brand_form = AdminBrandForm(request.POST, request.FILES)
            if brand_form.is_valid():
                brand = brand_form.save()
                log_admin_action(request.user, f"Created brand '{brand.name}'", 'Brand', brand.id)
                messages.success(request, f"Brand '{brand.name}' added.")
                return redirect('shop:admin_categories_brands')

    return render(
        request,
        'admin_panel/categories_brands.html',
        {
            'admin_section': 'categories',
            'categories': Category.objects.all(),
            'brands': Brand.objects.all(),
            'category_form': category_form,
            'brand_form': brand_form,
        }
    )


@staff_required
@require_POST
def admin_category_delete(request, category_id):
    cat = get_object_or_404(Category, id=category_id)
    name = cat.name
    cat.delete()
    log_admin_action(request.user, f"Deleted category '{name}'", 'Category', category_id)
    messages.info(request, f"Category '{name}' deleted.")
    return redirect('shop:admin_categories_brands')


@staff_required
@require_POST
def admin_brand_delete(request, brand_id):
    brand = get_object_or_404(Brand, id=brand_id)
    name = brand.name
    brand.delete()
    log_admin_action(request.user, f"Deleted brand '{name}'", 'Brand', brand_id)
    messages.info(request, f"Brand '{name}' deleted.")
    return redirect('shop:admin_categories_brands')


@staff_required
def admin_orders(request):
    orders = Order.objects.select_related('user', 'promo_code').order_by('-created_at')
    search_q = (request.GET.get('q') or '').strip()
    selected_status = (request.GET.get('status') or '').strip()
    selected_payment = (request.GET.get('payment_status') or '').strip()

    if search_q:
        orders = orders.filter(
            Q(order_number__icontains=search_q)
            | Q(first_name__icontains=search_q)
            | Q(last_name__icontains=search_q)
            | Q(email__icontains=search_q)
            | Q(phone__icontains=search_q)
        )
    if selected_status:
        orders = orders.filter(status=selected_status)
    if selected_payment:
        orders = orders.filter(payment_status=selected_payment)

    return render(
        request,
        'admin_panel/orders.html',
        {
            'admin_section': 'orders',
            'orders': orders,
            'search_q': search_q,
            'selected_status': selected_status,
            'selected_payment': selected_payment,
            'status_choices': Order.STATUS_CHOICES,
            'payment_status_choices': Order.PAYMENT_STATUS_CHOICES,
        }
    )


@staff_required
def admin_order_detail(request, order_number):
    order = get_object_or_404(Order.objects.prefetch_related('items__product'), order_number=order_number)
    if request.method == 'POST':
        form = AdminOrderUpdateForm(request.POST, instance=order)
        if form.is_valid():
            updated = form.save()
            log_admin_action(
                request.user,
                f"Updated Order #{updated.order_number} -> status={updated.status}, payment={updated.payment_status}",
                'Order',
                updated.order_number
            )
            messages.success(request, f"Order #{updated.order_number} status updated.")
            return redirect('shop:admin_order_detail', order_number=updated.order_number)
    else:
        form = AdminOrderUpdateForm(instance=order)

    return render(
        request,
        'admin_panel/order_detail.html',
        {'admin_section': 'orders', 'order': order, 'form': form}
    )


@staff_required
def admin_customers(request):
    customers = User.objects.annotate(order_count=Count('orders')).order_by('-date_joined')
    search_q = (request.GET.get('q') or '').strip()
    if search_q:
        customers = customers.filter(
            Q(username__icontains=search_q)
            | Q(email__icontains=search_q)
            | Q(first_name__icontains=search_q)
            | Q(last_name__icontains=search_q)
            | Q(phone_num__icontains=search_q)
        )
    return render(
        request,
        'admin_panel/customers.html',
        {'admin_section': 'customers', 'customers': customers, 'search_q': search_q}
    )


@staff_required
def admin_customer_detail(request, user_id):
    customer = get_object_or_404(User, id=user_id)
    customer_orders = Order.objects.filter(user=customer).order_by('-created_at')
    customer_reviews = Review.objects.filter(user=customer).select_related('product')
    return render(
        request,
        'admin_panel/customer_detail.html',
        {
            'admin_section': 'customers',
            'customer': customer,
            'customer_orders': customer_orders,
            'customer_reviews': customer_reviews,
        }
    )


@staff_required
@require_POST
def admin_customer_toggle_active(request, user_id):
    customer = get_object_or_404(User, id=user_id)
    if customer.id == request.user.id:
        messages.error(request, "You cannot deactivate your own account.")
        return redirect('shop:admin_customers')
    customer.is_active = not customer.is_active
    customer.save(update_fields=['is_active'])
    state = 'activated' if customer.is_active else 'deactivated'
    log_admin_action(request.user, f"{state.capitalize()} customer @{customer.username}", 'User', customer.id)
    messages.info(request, f"Customer @{customer.username} has been {state}.")
    return redirect('shop:admin_customers')


@staff_required
def admin_reviews(request):
    reviews = Review.objects.select_related('user', 'product').order_by('-created_at')
    search_q = (request.GET.get('q') or '').strip()
    selected_rating = (request.GET.get('rating') or '').strip()

    if search_q:
        reviews = reviews.filter(
            Q(title__icontains=search_q)
            | Q(body__icontains=search_q)
            | Q(user__username__icontains=search_q)
            | Q(product__name__icontains=search_q)
        )
    if selected_rating.isdigit():
        reviews = reviews.filter(rating=int(selected_rating))

    return render(
        request,
        'admin_panel/reviews.html',
        {
            'admin_section': 'reviews',
            'reviews': reviews,
            'search_q': search_q,
            'selected_rating': selected_rating,
            'rating_choices': Review.RATING_CHOICES,
        }
    )


@staff_required
@require_POST
def admin_review_toggle(request, review_id):
    review = get_object_or_404(Review, id=review_id)
    review.is_approved = not review.is_approved
    review.save(update_fields=['is_approved'])
    log_admin_action(
        request.user,
        f"Moderated review #{review.id} -> approved={review.is_approved}",
        'Review',
        review.id
    )
    messages.info(request, f"Review #{review.id} visibility updated.")
    return redirect('shop:admin_reviews')


@staff_required
@require_POST
def admin_review_delete(request, review_id):
    review = get_object_or_404(Review, id=review_id)
    review.delete()
    log_admin_action(request.user, f"Deleted review #{review_id}", 'Review', review_id)
    messages.info(request, "Review deleted.")
    return redirect('shop:admin_reviews')


@staff_required
def admin_discounts(request):
    discount_form = AdminDiscountForm()
    promo_form = AdminPromoCodeForm()

    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        if form_type == 'discount':
            discount_form = AdminDiscountForm(request.POST)
            if discount_form.is_valid():
                disc = discount_form.save()
                log_admin_action(request.user, f"Created discount '{disc.name}'", 'Discount', disc.id)
                messages.success(request, f"Discount campaign '{disc.name}' created.")
                return redirect('shop:admin_discounts')
        elif form_type == 'promo':
            promo_form = AdminPromoCodeForm(request.POST)
            if promo_form.is_valid():
                promo = promo_form.save()
                log_admin_action(request.user, f"Created promo code '{promo.code}'", 'PromoCode', promo.id)
                messages.success(request, f"Promotional code '{promo.code}' created.")
                return redirect('shop:admin_discounts')

    return render(
        request,
        'admin_panel/discounts.html',
        {
            'admin_section': 'discounts',
            'discounts': Discount.objects.prefetch_related('products', 'categories').all(),
            'promo_codes': PromoCode.objects.all(),
            'discount_form': discount_form,
            'promo_form': promo_form,
        }
    )


@staff_required
@require_POST
def admin_discount_toggle(request, discount_id):
    disc = get_object_or_404(Discount, id=discount_id)
    disc.is_active = not disc.is_active
    disc.save(update_fields=['is_active'])
    log_admin_action(request.user, f"Toggled discount '{disc.name}' -> {disc.is_active}", 'Discount', disc.id)
    messages.info(request, f"Discount '{disc.name}' status updated.")
    return redirect('shop:admin_discounts')


@staff_required
@require_POST
def admin_discount_delete(request, discount_id):
    disc = get_object_or_404(Discount, id=discount_id)
    name = disc.name
    disc.delete()
    log_admin_action(request.user, f"Deleted discount '{name}'", 'Discount', discount_id)
    messages.info(request, f"Discount '{name}' deleted.")
    return redirect('shop:admin_discounts')


@staff_required
@require_POST
def admin_promo_toggle(request, promo_id):
    promo = get_object_or_404(PromoCode, id=promo_id)
    promo.is_active = not promo.is_active
    promo.save(update_fields=['is_active'])
    log_admin_action(request.user, f"Toggled promo code '{promo.code}' -> {promo.is_active}", 'PromoCode', promo.id)
    messages.info(request, f"Promo code '{promo.code}' status updated.")
    return redirect('shop:admin_discounts')


@staff_required
@require_POST
def admin_promo_delete(request, promo_id):
    promo = get_object_or_404(PromoCode, id=promo_id)
    code = promo.code
    promo.delete()
    log_admin_action(request.user, f"Deleted promo code '{code}'", 'PromoCode', promo_id)
    messages.info(request, f"Promo code '{code}' deleted.")
    return redirect('shop:admin_discounts')
