from decimal import Decimal, ROUND_HALF_UP
from django.db import models
from django.db.models import Avg, Sum
from django.contrib.auth.models import AbstractUser
from django.urls import reverse
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from .validators import validate_image_upload


class User(AbstractUser):
    image = models.ImageField(
        upload_to='media/users_images',
        blank=True,
        validators=[validate_image_upload]
    )
    phone_num = models.CharField(blank=True, max_length=30)
    address = models.CharField(blank=True, max_length=255)
    city = models.CharField(blank=True, max_length=100)
    postal_code = models.CharField(blank=True, max_length=20)
    bio = models.TextField(blank=True, max_length=500)

    class Meta:
        ordering = ('username',)
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.username

    @property
    def full_name(self):
        name = f"{self.first_name} {self.last_name}".strip()
        return name if name else self.username

    @property
    def total_orders_count(self):
        return self.orders.count()

    @property
    def total_reviews_count(self):
        return self.review_set.count()

    @property
    def total_spent(self):
        total = self.orders.exclude(status='cancelled').aggregate(total=Sum('total_amount'))['total']
        return total or Decimal('0.00')


class Category(models.Model):
    name = models.CharField(max_length=100, db_index=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(max_length=500, blank=True)
    icon = models.CharField(max_length=50, blank=True, default='cpu')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ('name',)
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('shop:product_list_by_category', args=[self.slug])


class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True, db_index=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(max_length=500, blank=True)
    logo = models.ImageField(upload_to='media/brands', blank=True, validators=[validate_image_upload])
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ('name',)
        verbose_name = 'Brand'
        verbose_name_plural = 'Brands'

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(
        Category,
        related_name='products',
        on_delete=models.CASCADE
    )
    brand = models.ForeignKey(
        Brand,
        related_name='products',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    name = models.CharField(max_length=150, db_index=True)
    slug = models.CharField(max_length=150, db_index=True, unique=True)
    sku = models.CharField(max_length=64, blank=True, db_index=True)
    image = models.ImageField(
        upload_to='media/%Y/%m/%d',
        blank=True,
        validators=[validate_image_upload]
    )
    description = models.TextField(max_length=2000, blank=True)
    short_specs = models.CharField(max_length=255, blank=True)
    specifications = models.TextField(
        blank=True,
        help_text="Enter one specification per line in 'Key: Value' format."
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    original_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    discount_percent = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(90)]
    )
    stock = models.PositiveIntegerField(default=15)
    available = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    sales_count = models.PositiveIntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True)
    uploaded = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('name',)
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        indexes = [
            models.Index(fields=['id', 'slug']),
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('shop:product_detail', args=[self.id, self.slug])

    @property
    def in_stock(self):
        return self.available and self.stock > 0

    def get_base_price(self):
        """Returns the reference original price before discounts."""
        if self.original_price and self.original_price > self.price:
            return self.original_price
        return self.price

    def get_final_price(self):
        """
        Calculates the final selling price taking into account:
        1. Direct `original_price` vs `price`
        2. Product-level `discount_percent`
        3. Active `Discount` campaigns on this product or its category
        All calculations use Decimal arithmetic and never fall below $0.01.
        """
        base = self.get_base_price()
        best_price = self.price

        if self.discount_percent and self.discount_percent > 0:
            multiplier = (Decimal('100') - Decimal(str(self.discount_percent))) / Decimal('100')
            pct_price = (base * multiplier).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            if pct_price < best_price:
                best_price = pct_price

        now = timezone.now()
        try:
            active_discounts = list(
                self.discounts.filter(is_active=True, start_date__lte=now)
            ) + list(
                self.category.discounts.filter(is_active=True, start_date__lte=now)
            )
            for discount in active_discounts:
                if discount.end_date and discount.end_date < now:
                    continue
                candidate = discount.calculate_discounted_price(base)
                if candidate < best_price:
                    best_price = candidate
        except Exception:
            pass

        return max(best_price, Decimal('0.01'))

    @property
    def discounted_price(self):
        return self.get_final_price()

    @property
    def display_original_price(self):
        return self.get_base_price()

    @property
    def has_discount(self):
        return self.get_final_price() < self.get_base_price()

    def get_discount_percentage(self):
        base = self.get_base_price()
        final = self.get_final_price()
        if base <= Decimal('0.00') or final >= base:
            return 0
        pct = ((base - final) / base * Decimal('100')).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        return int(pct)

    @property
    def discount_percentage(self):
        return self.get_discount_percentage()

    @property
    def average_rating(self):
        avg = self.reviews.filter(is_approved=True).aggregate(avg=Avg('rating'))['avg']
        return round(float(avg), 1) if avg else 0.0

    @property
    def review_count(self):
        return self.reviews.filter(is_approved=True).count()

    @property
    def specs_list(self):
        if not self.specifications:
            return []
        result = []
        for line in self.specifications.splitlines():
            line = line.strip()
            if not line:
                continue
            if ':' in line:
                k, v = line.split(':', 1)
                result.append((k.strip(), v.strip()))
            else:
                result.append(('Feature', line))
        return result


class Discount(models.Model):
    DISCOUNT_TYPE_CHOICES = (
        ('percentage', 'Percentage (%)'),
        ('fixed', 'Fixed Amount ($)'),
    )
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    discount_type = models.CharField(
        max_length=20,
        choices=DISCOUNT_TYPE_CHOICES,
        default='percentage'
    )
    value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    products = models.ManyToManyField(Product, related_name='discounts', blank=True)
    categories = models.ManyToManyField(Category, related_name='discounts', blank=True)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Discount'
        verbose_name_plural = 'Discounts'

    def __str__(self):
        return f"{self.name} ({self.get_discount_Label()})"

    def get_discount_Label(self):
        if self.discount_type == 'percentage':
            return f"-{self.value.normalize()}%"
        return f"-${self.value}"

    def is_valid_now(self):
        if not self.is_active:
            return False
        now = timezone.now()
        if self.start_date and self.start_date > now:
            return False
        if self.end_date and self.end_date < now:
            return False
        return True

    def calculate_discounted_price(self, base_price):
        base = Decimal(str(base_price))
        if self.discount_type == 'percentage':
            pct = min(self.value, Decimal('90.00'))
            discounted = base * (Decimal('100.00') - pct) / Decimal('100.00')
        else:
            discounted = base - self.value
        discounted = discounted.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return max(discounted, Decimal('0.01'))


class Review(models.Model):
    RATING_CHOICES = (
        (1, '1 Star'),
        (2, '2 Stars'),
        (3, '3 Stars'),
        (4, '4 Stars'),
        (5, '5 Stars'),
    )

    product = models.ForeignKey('Product', related_name='reviews', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    body = models.TextField()
    rating = models.IntegerField(choices=RATING_CHOICES, default=5)
    is_approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Review'
        verbose_name_plural = 'Reviews'

    def __str__(self):
        return f'{self.title} - {self.user.username}'


class Wishlist(models.Model):
    user = models.ForeignKey(User, related_name='wishlist_items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='wishlisted_by', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')
        ordering = ['-created_at']
        verbose_name = 'Wishlist Item'
        verbose_name_plural = 'Wishlist Items'

    def __str__(self):
        return f"{self.user.username} -> {self.product.name}"


class AdminAuditLog(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='admin_audit_logs'
    )
    action = models.CharField(max_length=120)
    target_model = models.CharField(max_length=80)
    target_id = models.CharField(max_length=64, blank=True)
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Admin Audit Log'
        verbose_name_plural = 'Admin Audit Logs'

    def __str__(self):
        actor = self.user.username if self.user else 'System'
        return f"[{self.created_at:%Y-%m-%d %H:%M}] {actor}: {self.action}"
