from decimal import Decimal
from datetime import timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.core.management import call_command
from io import StringIO

from .models import User, Category, Brand, Product, Discount, Review, Wishlist
from cart.models import PromoCode, Order, OrderItem


class ShopComprehensiveTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.now = timezone.now()

        # Users
        self.user1 = User.objects.create_user(
            username='alice',
            email='alice@example.com',
            password='StrongPassword123!',
            first_name='Alice',
            last_name='Builder',
            phone_num='+998901112233'
        )
        self.user2 = User.objects.create_user(
            username='bob',
            email='bob@example.com',
            password='StrongPassword123!',
            first_name='Bob',
            last_name='Gamer'
        )
        self.staff_user = User.objects.create_user(
            username='staffadmin',
            email='staff@example.com',
            password='StaffPassword123!',
            is_staff=True
        )

        # Categories & Brands
        self.cat_gpu = Category.objects.create(name='Graphics Cards', slug='graphics-cards')
        self.cat_cpu = Category.objects.create(name='Processors', slug='processors')
        self.brand_asus = Brand.objects.create(name='ASUS ROG', slug='asus-rog')
        self.brand_amd = Brand.objects.create(name='AMD', slug='amd')

        # Products
        self.product1 = Product.objects.create(
            category=self.cat_gpu,
            brand=self.brand_asus,
            name='ROG Strix RTX 4080 Super',
            slug='rog-strix-rtx-4080-super',
            sku='ROG-4080S',
            price=Decimal('999.00'),
            original_price=Decimal('1099.00'),
            stock=10,
            available=True,
            is_featured=True,
            sales_count=25,
            specifications='VRAM: 16GB GDDR6X\nBoost Clock: 2640 MHz'
        )
        self.product2 = Product.objects.create(
            category=self.cat_cpu,
            brand=self.brand_amd,
            name='AMD Ryzen 7 7800X3D',
            slug='amd-ryzen-7-7800x3d',
            sku='RYZEN-7800X3D',
            price=Decimal('399.00'),
            stock=5,
            available=True,
            sales_count=50
        )

    # 1. Homepage
    def test_01_homepage_loads(self):
        response = self.client.get(reverse('shop:product_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ROG Strix RTX 4080 Super')
        self.assertContains(response, 'AMD Ryzen 7 7800X3D')

    # 2. Product Catalog & Category Page
    def test_02_product_catalog_and_category_filtering(self):
        response = self.client.get(reverse('shop:catalog'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ROG Strix RTX 4080 Super')

        cat_response = self.client.get(
            reverse('shop:product_list_by_category', args=[self.cat_gpu.slug])
        )
        self.assertEqual(cat_response.status_code, 200)
        self.assertContains(cat_response, 'ROG Strix RTX 4080 Super')
        self.assertNotContains(cat_response, 'AMD Ryzen 7 7800X3D')

    # 3. Product Details
    def test_03_product_details_page(self):
        response = self.client.get(
            reverse('shop:product_detail', args=[self.product1.id, self.product1.slug])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ROG Strix RTX 4080 Super')
        self.assertContains(response, '16GB GDDR6X')
        self.assertContains(response, '999.00')

    # 4. Search
    def test_04_product_search(self):
        response = self.client.get(reverse('shop:catalog'), {'q': '7800X3D'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'AMD Ryzen 7 7800X3D')
        self.assertNotContains(response, 'ROG Strix RTX 4080 Super')

    # 5. Filtering (Price & Brand & Stock)
    def test_05_catalog_price_and_brand_filtering(self):
        response = self.client.get(
            reverse('shop:catalog'),
            {'min_price': '500', 'max_price': '1200', 'brand': 'asus-rog'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ROG Strix RTX 4080 Super')
        self.assertNotContains(response, 'AMD Ryzen 7 7800X3D')

    # 6. Sorting
    def test_06_catalog_sorting(self):
        resp_asc = self.client.get(reverse('shop:catalog'), {'sort': 'price_asc'})
        products_asc = list(resp_asc.context['products'])
        self.assertEqual(products_asc[0], self.product2)
        self.assertEqual(products_asc[1], self.product1)

        resp_desc = self.client.get(reverse('shop:catalog'), {'sort': 'price_desc'})
        products_desc = list(resp_desc.context['products'])
        self.assertEqual(products_desc[0], self.product1)
        self.assertEqual(products_desc[1], self.product2)

        resp_pop = self.client.get(reverse('shop:catalog'), {'sort': 'popular'})
        products_pop = list(resp_pop.context['products'])
        self.assertEqual(products_pop[0], self.product2)

    # 7. Registration & Unique Email/Username Validation
    def test_07_user_registration_and_unique_validation(self):
        resp = self.client.post(reverse('shop:register'), {
            'username': 'newbuilder',
            'email': 'newbuilder@example.com',
            'first_name': 'New',
            'last_name': 'Builder',
            'phone_num': '+998901234567',
            'password1': 'ComplexPass987!',
            'password2': 'ComplexPass987!',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(User.objects.filter(username='newbuilder').exists())

        # Duplicate email should fail validation
        dup_resp = self.client.post(reverse('shop:register'), {
            'username': 'anotheruser',
            'email': 'alice@example.com',
            'password1': 'ComplexPass987!',
            'password2': 'ComplexPass987!',
        })
        self.assertEqual(dup_resp.status_code, 200)
        self.assertFalse(User.objects.filter(username='anotheruser').exists())

    # 8 & 9. Login and Logout
    def test_08_09_login_and_logout(self):
        login_resp = self.client.post(reverse('shop:login'), {
            'username': 'alice',
            'password': 'StrongPassword123!'
        })
        self.assertEqual(login_resp.status_code, 302)

        logout_resp = self.client.get(reverse('shop:logout'))
        self.assertEqual(logout_resp.status_code, 302)

    # 10. Password Recovery Flow
    def test_10_password_recovery_flow(self):
        resp = self.client.get(reverse('shop:password_reset'))
        self.assertEqual(resp.status_code, 200)
        post_resp = self.client.post(reverse('shop:password_reset'), {'email': 'alice@example.com'})
        self.assertEqual(post_resp.status_code, 302)

    # 11. Profile Editing
    def test_11_profile_editing(self):
        self.client.login(username='alice', password='StrongPassword123!')
        resp = self.client.post(reverse('shop:profile_edit'), {
            'username': 'alice',
            'email': 'alice@example.com',
            'first_name': 'AliceUpdated',
            'last_name': 'Builder',
            'phone_num': '+998909998877',
            'address': 'Navoi Street 12',
            'city': 'Tashkent',
            'postal_code': '100011',
            'bio': 'Custom watercooling enthusiast'
        })
        self.assertEqual(resp.status_code, 302)
        self.user1.refresh_from_db()
        self.assertEqual(self.user1.first_name, 'AliceUpdated')
        self.assertEqual(self.user1.city, 'Tashkent')

    # 12 & 23. User Permissions & Admin Permissions
    def test_12_23_user_and_admin_permissions(self):
        # Anonymous user redirected from private dashboard & admin panel
        resp_anon = self.client.get(reverse('shop:user_dashboard'))
        self.assertEqual(resp_anon.status_code, 302)
        resp_anon_admin = self.client.get(reverse('shop:admin_dashboard'))
        self.assertEqual(resp_anon_admin.status_code, 302)

        # Regular customer gets 403 Forbidden on Custom Admin Dashboard
        self.client.login(username='alice', password='StrongPassword123!')
        resp_cust_admin = self.client.get(reverse('shop:admin_dashboard'))
        self.assertEqual(resp_cust_admin.status_code, 403)

        # Staff user can access Custom Admin Dashboard (200 OK)
        self.client.login(username='staffadmin', password='StaffPassword123!')
        resp_staff_admin = self.client.get(reverse('shop:admin_dashboard'))
        self.assertEqual(resp_staff_admin.status_code, 200)

    # 13. Wishlist
    def test_13_wishlist_toggle_and_view(self):
        self.client.login(username='alice', password='StrongPassword123!')
        # Add to wishlist
        self.client.post(reverse('shop:wishlist_toggle', args=[self.product1.id]))
        self.assertTrue(Wishlist.objects.filter(user=self.user1, product=self.product1).exists())

        list_resp = self.client.get(reverse('shop:wishlist'))
        self.assertEqual(list_resp.status_code, 200)
        self.assertContains(list_resp, self.product1.name)

        # Toggle again removes from wishlist
        self.client.post(reverse('shop:wishlist_toggle', args=[self.product1.id]))
        self.assertFalse(Wishlist.objects.filter(user=self.user1, product=self.product1).exists())

    # 18, 19, 20. Review Creation, Editing, Deletion & Ownership Protection
    def test_18_19_20_review_crud_and_ownership_protection(self):
        self.client.login(username='alice', password='StrongPassword123!')
        # Create review
        create_resp = self.client.post(
            reverse('shop:add_review', args=[self.product1.id]),
            {'title': 'Awesome GPU', 'rating': 5, 'body': 'Super quiet and fast!'}
        )
        self.assertEqual(create_resp.status_code, 302)
        review = Review.objects.get(user=self.user1, product=self.product1)
        self.assertEqual(review.title, 'Awesome GPU')

        # Edit own review
        edit_resp = self.client.post(
            reverse('shop:edit_review', args=[review.id]),
            {'title': 'Updated Title', 'rating': 4, 'body': 'Still great after 2 months.'}
        )
        self.assertEqual(edit_resp.status_code, 302)
        review.refresh_from_db()
        self.assertEqual(review.title, 'Updated Title')

        # Another user (bob) CANNOT edit or delete alice's review
        self.client.login(username='bob', password='StrongPassword123!')
        forbidden_edit = self.client.post(
            reverse('shop:edit_review', args=[review.id]),
            {'title': 'Hacked', 'rating': 1, 'body': 'Hacked'}
        )
        self.assertEqual(forbidden_edit.status_code, 404)
        forbidden_del = self.client.post(reverse('shop:delete_review', args=[review.id]))
        self.assertEqual(forbidden_del.status_code, 404)
        self.assertTrue(Review.objects.filter(id=review.id).exists())

        # Alice can delete her own review
        self.client.login(username='alice', password='StrongPassword123!')
        del_resp = self.client.post(reverse('shop:delete_review', args=[review.id]))
        self.assertEqual(del_resp.status_code, 302)
        self.assertFalse(Review.objects.filter(id=review.id).exists())

    # 21. Discount Calculations (Product & Category Discounts)
    def test_21_discount_calculations(self):
        # Product1 has price=999, original_price=1099 (9% off)
        self.assertTrue(self.product1.has_discount)
        self.assertEqual(self.product1.get_final_price(), Decimal('999.00'))

        # Add a 20% category campaign discount on Graphics Cards
        disc = Discount.objects.create(
            name='GPU Mega Sale',
            discount_type='percentage',
            value=Decimal('20.00'),
            start_date=self.now - timedelta(days=1),
            end_date=self.now + timedelta(days=5),
            is_active=True
        )
        disc.categories.add(self.cat_gpu)
        # 20% off base original_price 1099.00 = 879.20
        self.assertEqual(self.product1.get_final_price(), Decimal('879.20'))
        self.assertEqual(self.product1.get_discount_percentage(), 20)

    # 24 & 25. Admin Product Management & Order Management
    def test_24_25_admin_product_and_order_management(self):
        self.client.login(username='staffadmin', password='StaffPassword123!')

        # Create product via custom admin
        add_resp = self.client.post(reverse('shop:admin_product_add'), {
            'name': 'Corsair Vengeance 32GB DDR5',
            'slug': 'corsair-vengeance-32gb-ddr5',
            'sku': 'COR-DDR5-32',
            'category': self.cat_cpu.id,
            'brand': self.brand_asus.id,
            'price': '119.99',
            'discount_percent': '0',
            'stock': '20',
            'available': 'on',
            'short_specs': '32GB (2x16GB) DDR5-6000',
            'description': 'High speed memory kit.',
        })
        self.assertEqual(add_resp.status_code, 302)
        new_prod = Product.objects.get(slug='corsair-vengeance-32gb-ddr5')
        self.assertEqual(new_prod.price, Decimal('119.99'))

        # Create order and update its status via custom admin
        order = Order.objects.create(
            user=self.user1,
            first_name='Alice',
            last_name='Builder',
            email='alice@example.com',
            phone='+998901112233',
            address='Amir Temur 10',
            city='Tashkent',
            status='pending',
            payment_status='pending',
            subtotal=Decimal('399.00'),
            total_amount=Decimal('399.00')
        )
        ord_resp = self.client.post(
            reverse('shop:admin_order_detail', args=[order.order_number]),
            {'status': 'shipped', 'payment_status': 'paid', 'notes': 'Dispatched via courier'}
        )
        self.assertEqual(ord_resp.status_code, 302)
        order.refresh_from_db()
        self.assertEqual(order.status, 'shipped')
        self.assertEqual(order.payment_status, 'paid')

    # 26. Database Migrations Check
    def test_26_migrations_are_consistent(self):
        out = StringIO()
        call_command('makemigrations', '--check', '--dry-run', stdout=out)
        self.assertIn('No changes detected', out.getvalue())
