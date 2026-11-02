from django.contrib import admin
from .models import PromoCode, Order, OrderItem


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = [
        'code', 'discount_type', 'discount_value', 'min_order_amount',
        'used_count', 'usage_limit', 'valid_from', 'valid_until', 'is_active'
    ]
    list_filter = ['discount_type', 'is_active', 'valid_from']
    search_fields = ['code', 'description']


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ['product']
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'order_number', 'user', 'first_name', 'last_name', 'email',
        'status', 'payment_status', 'total_amount', 'created_at'
    ]
    list_filter = ['status', 'payment_status', 'payment_method', 'created_at']
    search_fields = ['order_number', 'first_name', 'last_name', 'email', 'phone']
    inlines = [OrderItemInline]
