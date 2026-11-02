import uuid
from decimal import Decimal, ROUND_HALF_UP
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator


class PromoCode(models.Model):
    DISCOUNT_TYPE_CHOICES = (
        ('percentage', 'Percentage (%)'),
        ('fixed', 'Fixed Amount ($)'),
    )

    code = models.CharField(max_length=50, unique=True, db_index=True)
    description = models.CharField(max_length=255, blank=True)
    discount_type = models.CharField(
        max_length=20,
        choices=DISCOUNT_TYPE_CHOICES,
        default='percentage'
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    min_order_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    usage_limit = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum number of times this code can be used. Leave empty for unlimited."
    )
    used_count = models.PositiveIntegerField(default=0)
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Promotional Code'
        verbose_name_plural = 'Promotional Codes'

    def __str__(self):
        return f"{self.code} ({self.get_discount_display_label()})"

    def save(self, *args, **kwargs):
        if self.code:
            self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    def get_discount_display_label(self):
        if self.discount_type == 'percentage':
            return f"{self.discount_value.normalize()}% OFF"
        return f"${self.discount_value} OFF"

    @property
    def is_expired(self):
        now = timezone.now()
        return bool(self.valid_until and self.valid_until < now)

    @property
    def is_usage_exceeded(self):
        return bool(self.usage_limit is not None and self.used_count >= self.usage_limit)

    def validate_for_cart(self, subtotal):
        """
        Server-side validation of promo code against current timestamp, usage limits, and cart subtotal.
        Returns (is_valid: bool, message: str).
        """
        now = timezone.now()
        if not self.is_active:
            return False, "This promotional code is currently inactive."
        if self.valid_from and self.valid_from > now:
            return False, "This promotional code is not yet active."
        if self.valid_until and self.valid_until < now:
            return False, "This promotional code has expired."
        if self.usage_limit is not None and self.used_count >= self.usage_limit:
            return False, "This promotional code has reached its usage limit."
        if subtotal is not None and Decimal(str(subtotal)) < self.min_order_amount:
            return False, f"Minimum order amount of ${self.min_order_amount} is required for this promo code."
        return True, "Promotional code applied!"

    def calculate_discount(self, subtotal):
        """
        Calculates the discount amount in Decimal, ensuring the discount never exceeds subtotal
        (preventing negative order totals).
        """
        subtotal = Decimal(str(subtotal))
        if subtotal <= Decimal('0.00'):
            return Decimal('0.00')
        is_ok, _ = self.validate_for_cart(subtotal)
        if not is_ok:
            return Decimal('0.00')

        if self.discount_type == 'percentage':
            pct = min(self.discount_value, Decimal('100.00'))
            discount = (subtotal * pct / Decimal('100.00')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        else:
            discount = self.discount_value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        return min(discount, subtotal)


class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    )

    PAYMENT_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    )

    PAYMENT_METHOD_CHOICES = (
        ('cod', 'Pay on Delivery (Cash / Terminal)'),
        ('bank_transfer', 'Bank Transfer / Corporate Invoice'),
        ('online_pending', 'Online Card Payment (Awaiting Provider Gateway)'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='orders',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    order_number = models.CharField(max_length=32, unique=True, db_index=True, editable=False)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=30)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20, blank=True)
    notes = models.TextField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    payment_method = models.CharField(
        max_length=30,
        choices=PAYMENT_METHOD_CHOICES,
        default='cod'
    )

    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    promo_code = models.ForeignKey(
        PromoCode,
        related_name='orders',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'

    def __str__(self):
        return f"Order #{self.order_number}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            timestamp_part = timezone.now().strftime('%y%m%d')
            random_part = uuid.uuid4().hex[:6].upper()
            self.order_number = f"PCS-{timestamp_part}-{random_part}"
        super().save(*args, **kwargs)

    @property
    def customer_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        related_name='items',
        on_delete=models.CASCADE
    )
    product = models.ForeignKey(
        'shop.Product',
        related_name='order_items',
        on_delete=models.SET_NULL,
        null=True
    )
    product_name = models.CharField(max_length=150)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    original_unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'

    def __str__(self):
        return f"{self.product_name} x {self.quantity} ({self.order.order_number})"

    def get_cost(self):
        return (self.price * self.quantity).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
