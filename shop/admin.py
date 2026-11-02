from django.contrib import admin
from django.utils.safestring import mark_safe
from .models import User, Category, Brand, Product, Discount, Review, Wishlist, AdminAuditLog


@admin.register(User)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'image_show']
    list_display_links = ['username', 'email']
    list_filter = ['is_staff', 'is_active', 'date_joined']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'phone_num']

    def image_show(self, obj):
        if obj.image:
            return mark_safe(f"<img src='{obj.image.url}' width='48' style='border-radius:6px;' />")
        return "None"

    image_show.short_description = "Avatar"


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'icon', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'category', 'brand', 'image_show', 'price',
        'original_price', 'discount_percent', 'stock', 'available', 'is_featured', 'sales_count'
    ]
    list_filter = ['available', 'is_featured', 'category', 'brand', 'created']
    list_editable = ['price', 'stock', 'available', 'is_featured']
    search_fields = ['name', 'slug', 'sku', 'description']
    prepopulated_fields = {'slug': ('name',)}

    def image_show(self, obj):
        if obj.image:
            return mark_safe(f"<img src='{obj.image.url}' width='56' style='border-radius:6px;' />")
        return "None"

    image_show.short_description = "Image"


@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = ['name', 'discount_type', 'value', 'start_date', 'end_date', 'is_active']
    list_filter = ['discount_type', 'is_active', 'start_date']
    search_fields = ['name', 'description']
    filter_horizontal = ['products', 'categories']


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['title', 'product', 'rating', 'user', 'is_approved', 'created_at']
    list_filter = ['rating', 'is_approved', 'created_at']
    list_editable = ['is_approved']
    search_fields = ['title', 'body', 'user__username', 'product__name']
    list_display_links = ['title', 'product']


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'created_at']
    search_fields = ['user__username', 'product__name']


@admin.register(AdminAuditLog)
class AdminAuditLogAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'user', 'action', 'target_model', 'target_id']
    list_filter = ['target_model', 'created_at']
    search_fields = ['action', 'details', 'user__username']
    readonly_fields = ['created_at', 'user', 'action', 'target_model', 'target_id', 'details']
