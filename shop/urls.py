from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from . import views

app_name = 'shop'

urlpatterns = [
    # Storefront & Catalog (preserving existing URL names)
    path('', views.product_list, name='product_list'),
    path('catalog/', views.catalog_view, name='catalog'),
    path('category/<slug:category_slug>/', views.product_list, name='product_list_by_category'),
    path('product/<int:id>/<slug:slug>/', views.product_detail, name='product_detail'),

    # Authentication & Password Recovery
    path('login/', views.loginuser, name='login'),
    path('logout/', views.logoutuser, name='logout'),
    path('register/', views.register, name='register'),
    path(
        'password-reset/',
        auth_views.PasswordResetView.as_view(
            template_name='users/password_reset.html',
            email_template_name='users/password_reset_email.html',
            success_url=reverse_lazy('shop:password_reset_done')
        ),
        name='password_reset'
    ),
    path(
        'password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='users/password_reset_done.html'
        ),
        name='password_reset_done'
    ),
    path(
        'password-reset-confirm/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='users/password_reset_confirm.html',
            success_url=reverse_lazy('shop:password_reset_complete')
        ),
        name='password_reset_confirm'
    ),
    path(
        'password-reset-complete/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='users/password_reset_complete.html'
        ),
        name='password_reset_complete'
    ),

    # User Account, Profile, Orders, Reviews & Wishlist
    path('account/', views.user_dashboard, name='user_dashboard'),
    path('account/profile/', views.profile_edit, name='profile_edit'),
    path('account/password/', views.password_change_view, name='password_change'),
    path('account/orders/', views.order_history, name='order_history'),
    path('account/orders/<str:order_number>/', views.user_order_detail, name='user_order_detail'),
    path('account/reviews/', views.user_reviews, name='user_reviews'),
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('wishlist/toggle/<int:product_id>/', views.wishlist_toggle, name='wishlist_toggle'),

    # Customer Review Actions
    path('add_review/<int:product_id>/', views.add_review, name='add_review'),
    path('review/<int:review_id>/edit/', views.edit_review, name='edit_review'),
    path('review/<int:review_id>/delete/', views.delete_review, name='delete_review'),

    # Custom Administration Panel (/dashboard/...)
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/products/', views.admin_products, name='admin_products'),
    path('dashboard/products/add/', views.admin_product_add, name='admin_product_add'),
    path('dashboard/products/<int:product_id>/edit/', views.admin_product_edit, name='admin_product_edit'),
    path('dashboard/products/<int:product_id>/toggle/', views.admin_product_toggle, name='admin_product_toggle'),
    path('dashboard/products/<int:product_id>/delete/', views.admin_product_delete, name='admin_product_delete'),
    path('dashboard/catalog-meta/', views.admin_categories_brands, name='admin_categories_brands'),
    path('dashboard/categories/<int:category_id>/delete/', views.admin_category_delete, name='admin_category_delete'),
    path('dashboard/brands/<int:brand_id>/delete/', views.admin_brand_delete, name='admin_brand_delete'),
    path('dashboard/orders/', views.admin_orders, name='admin_orders'),
    path('dashboard/orders/<str:order_number>/', views.admin_order_detail, name='admin_order_detail'),
    path('dashboard/customers/', views.admin_customers, name='admin_customers'),
    path('dashboard/customers/<int:user_id>/', views.admin_customer_detail, name='admin_customer_detail'),
    path('dashboard/customers/<int:user_id>/toggle-active/', views.admin_customer_toggle_active, name='admin_customer_toggle_active'),
    path('dashboard/reviews/', views.admin_reviews, name='admin_reviews'),
    path('dashboard/reviews/<int:review_id>/toggle/', views.admin_review_toggle, name='admin_review_toggle'),
    path('dashboard/reviews/<int:review_id>/delete/', views.admin_review_delete, name='admin_review_delete'),
    path('dashboard/discounts/', views.admin_discounts, name='admin_discounts'),
    path('dashboard/discounts/<int:discount_id>/toggle/', views.admin_discount_toggle, name='admin_discount_toggle'),
    path('dashboard/discounts/<int:discount_id>/delete/', views.admin_discount_delete, name='admin_discount_delete'),
    path('dashboard/promos/<int:promo_id>/toggle/', views.admin_promo_toggle, name='admin_promo_toggle'),
    path('dashboard/promos/<int:promo_id>/delete/', views.admin_promo_delete, name='admin_promo_delete'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
