from decimal import Decimal
from datetime import timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from shop.models import User, Category, Product
from .models import PromoCode, Order, OrderItem


class CartCheckoutPromoTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.now = timezone.now()

        self.user1 = User.objects.create_user(
            username='buyer1',
            email='buyer1@example.com',
            password='BuyerPassword123!'
        )
        self.user2 = User.objects.create_user(
            username='buyer2',
            email='buyer2@example.com',
            password='BuyerPassword123!'
        )

        self.category = Category.objects.create(name='Keyboards', slug='keyboards')
        self.product = Product.objects.create(
            category=self.category,
            name='Keychron Q1 Pro Wireless',
            slug='keychron-q1-pro',
            price=Decimal('200.00'),
            stock=5,
            available=True
        )

        self.valid_promo = PromoCode.objects.create(
            code='SAVE15',
            discount_type='percentage',
            discount_value=Decimal('15.00'),
            min_order_amount=Decimal('100.00'),
            usage_limit=2,
            used_count=0,
            valid_from=self.now - timedelta(days=1),
            valid_until=self.now + timedelta(days=10),
            is_active=True
        )
        self.expired_promo = PromoCode.objects.create(
            code='OLD50',
            discount_type='percentage',
            discount_value=Decimal('50.00'),
            min_order_amount=Decimal('10.00'),
            usage_limit=10,
            valid_from=self.now - timedelta(days=20),
            valid_until=self.now - timedelta(days=2),
            is_active=True
        )

    # 14. Cart Functionality (Add, Update, Remove, Totals)
    def test_14_cart_add_update_remove(self):
        # Add 2 units
        resp = self.client.post(
            reverse('cart:cart_add', args=[self.product.id]),
            {'quantity': 2, 'update': False}
        )
        self.assertEqual(resp.status_code, 302)

        detail_resp = self.client.get(reverse('cart:cart_detail'))
        self.assertEqual(detail_resp.status_code, 200)
        self.assertEqual(detail_resp.context['cart'].get_subtotal(), Decimal('400.00'))

        # Update quantity to 3
        self.client.post(
            reverse('cart:cart_add', args=[self.product.id]),
            {'quantity': 3, 'update': True}
        )
        detail_resp = self.client.get(reverse('cart:cart_detail'))
        self.assertEqual(detail_resp.context['cart'].get_subtotal(), Decimal('600.00'))

        # Remove item
        self.client.post(reverse('cart:cart_remove', args=[self.product.id]))
        detail_resp = self.client.get(reverse('cart:cart_detail'))
        self.assertEqual(len(detail_resp.context['cart']), 0)

    # 22. Promotional Codes (Valid, Expired, Usage Limit, Negative Total Prevention)
    def test_22_promotional_codes_validation(self):
        self.client.post(
            reverse('cart:cart_add', args=[self.product.id]),
            {'quantity': 1, 'update': False}
        )

        # Apply expired code -> should not apply
        self.client.post(reverse('cart:promo_apply'), {'code': 'OLD50'})
        detail_resp = self.client.get(reverse('cart:cart_detail'))
        self.assertEqual(detail_resp.context['cart'].get_discount(), Decimal('0.00'))

        # Apply valid code SAVE15 (15% of 200 = 30.00 discount, total = 170.00)
        self.client.post(reverse('cart:promo_apply'), {'code': 'save15'})
        detail_resp = self.client.get(reverse('cart:cart_detail'))
        self.assertEqual(detail_resp.context['cart'].get_discount(), Decimal('30.00'))
        self.assertEqual(detail_resp.context['cart'].get_total_price(), Decimal('170.00'))

        # Fixed promo larger than subtotal must never result in negative order total
        huge_promo = PromoCode.objects.create(
            code='HUGE500',
            discount_type='fixed',
            discount_value=Decimal('500.00'),
            min_order_amount=Decimal('10.00'),
            is_active=True
        )
        self.assertEqual(huge_promo.calculate_discount(Decimal('200.00')), Decimal('200.00'))

    # 15, 16, 17. Checkout, Order Creation, Stock Deduction & Order Ownership
    def test_15_16_17_checkout_order_creation_and_ownership(self):
        self.client.login(username='buyer1', password='BuyerPassword123!')
        self.client.post(
            reverse('cart:cart_add', args=[self.product.id]),
            {'quantity': 2, 'update': False}
        )
        self.client.post(reverse('cart:promo_apply'), {'code': 'SAVE15'})

        checkout_resp = self.client.post(reverse('cart:checkout'), {
            'first_name': 'Buyer',
            'last_name': 'One',
            'email': 'buyer1@example.com',
            'phone': '+998901234567',
            'address': '123 Tech Park',
            'city': 'Tashkent',
            'postal_code': '100000',
            'payment_method': 'cod',
            'notes': 'Call before delivery'
        })
        self.assertEqual(checkout_resp.status_code, 302)

        order = Order.objects.get(user=self.user1)
        # Subtotal = 2 * 200 = 400.00; 15% discount = 60.00; Total = 340.00
        self.assertEqual(order.subtotal, Decimal('400.00'))
        self.assertEqual(order.discount_amount, Decimal('60.00'))
        self.assertEqual(order.total_amount, Decimal('340.00'))
        self.assertEqual(order.payment_status, 'pending')

        # Verify stock was deducted (5 - 2 = 3) and promo usage incremented
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        self.valid_promo.refresh_from_db()
        self.assertEqual(self.valid_promo.used_count, 1)

        # Verify buyer1 can access their order detail
        own_resp = self.client.get(reverse('shop:user_order_detail', args=[order.order_number]))
        self.assertEqual(own_resp.status_code, 200)

        # Verify buyer2 CANNOT access buyer1's order detail (404)
        self.client.login(username='buyer2', password='BuyerPassword123!')
        other_resp = self.client.get(reverse('shop:user_order_detail', args=[order.order_number]))
        self.assertEqual(other_resp.status_code, 404)
        other_success_resp = self.client.get(reverse('cart:order_success', args=[order.order_number]))
        self.assertEqual(other_success_resp.status_code, 404)
