import os
from datetime import timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont
from shop.models import User, Category, Brand, Product, Discount, Review, Wishlist
from cart.models import PromoCode, Order, OrderItem


def generate_product_image(filename, title, subtitle, accent_hex="#3b82f6"):
    """Generates a clean, high-resolution product showcase card image using Pillow."""
    rel_dir = os.path.join('media', 'products')
    full_dir = os.path.join(settings.MEDIA_ROOT, rel_dir)
    os.makedirs(full_dir, exist_ok=True)
    full_path = os.path.join(full_dir, filename)

    if not os.path.exists(full_path):
        img = Image.new('RGB', (800, 600), color=(15, 23, 42))
        draw = ImageDraw.Draw(img)

        # Subtle grid & accent frame
        r = int(accent_hex[1:3], 16)
        g = int(accent_hex[3:5], 16)
        b = int(accent_hex[5:7], 16)

        for x in range(0, 800, 40):
            draw.line([(x, 0), (x, 600)], fill=(23, 33, 56), width=1)
        for y in range(0, 600, 40):
            draw.line([(0, y), (800, y)], fill=(23, 33, 56), width=1)

        # Hardware silhouette box
        draw.rounded_rectangle([140, 110, 660, 410], radius=24, fill=(30, 41, 59), outline=(r, g, b), width=4)
        draw.rounded_rectangle([180, 150, 620, 370], radius=14, fill=(15, 23, 42), outline=(51, 65, 85), width=2)

        # Accent bar
        draw.rounded_rectangle([260, 240, 540, 280], radius=8, fill=(r, g, b))

        font = ImageFont.load_default()
        draw.text((200, 185), subtitle.upper(), fill=(148, 163, 184), font=font)
        draw.text((295, 254), title[:28], fill=(255, 255, 255), font=font)
        draw.text((200, 330), "PC SHOP CERTIFIED HARDWARE", fill=(r, g, b), font=font)

        img.save(full_path, quality=92)

    return f"media/products/{filename}"


class Command(BaseCommand):
    help = "Enriches existing catalog data and seeds additional PC hardware products, brands, discounts, promo codes, reviews, and sample orders."

    def handle(self, *args, **options):
        now = timezone.now()

        # 1. Brands
        brands_data = [
            ('2E Gaming', '2e-gaming', 'Performance gaming peripherals and accessories.'),
            ('Sharkoon', 'sharkoon', 'German-engineered PC cases, keyboards, and gaming gear.'),
            ('ASUS ROG', 'asus-rog', 'Republic of Gamers flagship motherboards, GPUs, and displays.'),
            ('NVIDIA', 'nvidia', 'GeForce RTX graphics cards and AI computing architecture.'),
            ('AMD', 'amd', 'Ryzen processors and Radeon graphics solutions.'),
            ('Logitech G', 'logitech-g', 'Pro-grade wireless gaming mice, keyboards, and headsets.'),
            ('HyperX', 'hyperx', 'High-comfort gaming headsets, DDR5 memory, and peripherals.'),
            ('Samsung', 'samsung', 'NVMe PCIe 4.0/5.0 SSDs and Odyssey gaming monitors.'),
            ('LG UltraGear', 'lg-ultragear', 'Ultra-fast IPS and OLED gaming monitors.'),
        ]
        brands = {}
        for name, slug, desc in brands_data:
            brand, _ = Brand.objects.update_or_create(
                slug=slug,
                defaults={'name': name, 'description': desc, 'is_active': True}
            )
            brands[slug] = brand

        # 2. Categories (preserve existing Headphones, Keyboards, Monitors)
        categories_data = [
            ('Headphones', 'headphones', '7.1 Surround and studio-grade wireless gaming headsets.', 'headphones'),
            ('Keyboards', 'keyboards', 'Mechanical RGB, low-profile TKL, and hot-swappable keyboards.', 'keyboard'),
            ('Monitors', 'monitors', 'High-refresh 144Hz-360Hz QHD and 4K IPS/OLED gaming monitors.', 'monitor'),
            ('Graphics Cards', 'graphics-cards', 'Next-gen GeForce RTX and Radeon RX GPUs for 4K gaming.', 'gpu'),
            ('Processors', 'processors', 'Multi-core AMD Ryzen and Intel Core desktop CPUs.', 'cpu'),
            ('Gaming Mice', 'gaming-mice', 'Ultra-lightweight esports optical and wireless gaming mice.', 'mouse'),
            ('SSD & Storage', 'ssd-storage', 'Blazing-fast NVMe M.2 PCIe Gen4 and Gen5 solid state drives.', 'storage'),
        ]
        categories = {}
        for name, slug, desc, icon in categories_data:
            cat = Category.objects.filter(slug=slug).first() or Category.objects.filter(name__iexact=name).first()
            if cat:
                cat.name = name
                cat.description = desc
                cat.icon = icon
                cat.is_active = True
                cat.save()
            else:
                cat = Category.objects.create(
                    name=name, slug=slug, description=desc, icon=icon, is_active=True
                )
            categories[slug] = cat

        # 3. Enrich existing products (IDs 1 and 2 if present)
        p1 = Product.objects.filter(slug='2egaming17pro').first()
        if p1:
            p1.brand = brands['2e-gaming']
            p1.sku = '2E-HG17PRO-BK'
            p1.original_price = Decimal('59.00')
            p1.price = Decimal('45.00')
            p1.stock = 24
            p1.is_featured = True
            p1.short_specs = '50mm Drivers • 7.1 Virtual Surround • RGB Backlight • Noise-Cancelling Mic'
            p1.description = (
                'The 2E Gaming HG17 Pro headset delivers immersive 7.1 virtual surround sound '
                'with precision-tuned 50mm neodymium drivers. Designed for marathon gaming sessions '
                'with memory-foam ear cushions, breathable leatherette, and a flexible omnidirectional microphone.'
            )
            p1.specifications = (
                "Driver Diameter: 50 mm Neodymium\n"
                "Frequency Response: 20 Hz - 20,000 Hz\n"
                "Impedance: 32 Ohm\n"
                "Interface: USB + 3.5mm Jack\n"
                "Lighting: Dynamic RGB\n"
                "Weight: 310 g"
            )
            p1.sales_count = 18
            p1.save()

        p2 = Product.objects.filter(slug='purewritertklrgb').first()
        if p2:
            p2.brand = brands['sharkoon']
            p2.sku = 'SHK-PWTKL-RGB'
            p2.original_price = Decimal('85.00')
            p2.price = Decimal('70.00')
            p2.stock = 16
            p2.is_featured = True
            p2.short_specs = 'Low-Profile Kailh Red Switches • Tenkeyless Form Factor • Per-Key RGB'
            p2.description = (
                'The Sharkoon PureWriter TKL RGB combines ultra-flat mechanical Kailh low-profile switches '
                'with a compact frameless tenkeyless design. Featuring customizable per-key RGB illumination, '
                'N-key rollover, and detachable USB cables for effortless portability.'
            )
            p2.specifications = (
                "Switch Type: Kailh Low-Profile Mechanical Red\n"
                "Form Factor: Tenkeyless (87 Keys)\n"
                "Actuation Distance: 1.5 mm\n"
                "Operating Lifespan: 50 Million Keystrokes\n"
                "Illumination: 16.8M Per-Key RGB\n"
                "Dimensions: 355 x 127 x 23 mm"
            )
            p2.sales_count = 14
            p2.save()

        # 4. Seed additional PC Hardware products
        new_products = [
            {
                'name': 'ASUS ROG Strix GeForce RTX 4070 Super OC 12GB',
                'slug': 'asus-rog-strix-rtx-4070-super-12gb',
                'category': categories['graphics-cards'],
                'brand': brands['asus-rog'],
                'sku': 'ROG-STRIX-RTX4070S-O12G',
                'price': Decimal('649.00'),
                'original_price': Decimal('699.00'),
                'discount_percent': 0,
                'stock': 9,
                'is_featured': True,
                'sales_count': 27,
                'accent': '#ef4444',
                'short_specs': '12GB GDDR6X • DLSS 3.5 • Axial-tech Triple Fan • 2670 MHz Boost',
                'description': (
                    'Engineered with NVIDIA Ada Lovelace architecture and Axial-tech triple cooling, '
                    'the ASUS ROG Strix RTX 4070 Super OC crushes high-refresh 1440p and 4K ray-traced gaming '
                    'with whisper-quiet acoustics and Aura Sync RGB lighting.'
                ),
                'specifications': (
                    "GPU Engine: NVIDIA GeForce RTX 4070 SUPER\n"
                    "CUDA Cores: 7168\n"
                    "Video Memory: 12GB GDDR6X\n"
                    "Boost Clock: 2670 MHz (OC Mode)\n"
                    "Memory Bus: 192-bit\n"
                    "Recommended PSU: 750W\n"
                    "Outputs: 2x HDMI 2.1a, 3x DisplayPort 1.4a"
                ),
            },
            {
                'name': 'AMD Ryzen 7 7800X3D 8-Core AM5 Processor',
                'slug': 'amd-ryzen-7-7800x3d-processor',
                'category': categories['processors'],
                'brand': brands['amd'],
                'sku': 'AMD-100-100000910WOF',
                'price': Decimal('389.00'),
                'original_price': Decimal('449.00'),
                'discount_percent': 0,
                'stock': 19,
                'is_featured': True,
                'sales_count': 42,
                'accent': '#f97316',
                'short_specs': '8 Cores / 16 Threads • 96MB 3D V-Cache • Up to 5.0 GHz • Socket AM5',
                'description': (
                    'The ultimate gaming processor powered by AMD 3D V-Cache technology. With a massive '
                    '96MB L3 cache and 8 Zen 4 cores, the Ryzen 7 7800X3D delivers class-leading frame rates '
                    'and exceptional power efficiency on the AM5 platform.'
                ),
                'specifications': (
                    "Cores / Threads: 8 Cores / 16 Threads\n"
                    "Base Clock: 4.2 GHz\n"
                    "Max Boost Clock: Up to 5.0 GHz\n"
                    "L3 Cache: 96 MB (3D V-Cache)\n"
                    "Socket: AM5\n"
                    "Default TDP: 120W\n"
                    "Memory Support: DDR5 Dual Channel"
                ),
            },
            {
                'name': 'LG UltraGear 27GP850-B 27" Nano IPS QHD 180Hz Monitor',
                'slug': 'lg-ultragear-27gp850-qhd-180hz',
                'category': categories['monitors'],
                'brand': brands['lg-ultragear'],
                'sku': 'LG-27GP850-B',
                'price': Decimal('319.00'),
                'original_price': Decimal('379.00'),
                'discount_percent': 0,
                'stock': 12,
                'is_featured': True,
                'sales_count': 21,
                'accent': '#8b5cf6',
                'short_specs': '27" 2560x1440 Nano IPS • 180Hz (O/C) • 1ms GtG • NVIDIA G-SYNC Compatible',
                'description': (
                    'Experience breathtaking color accuracy and blazing 180Hz speed on a 27-inch QHD '
                    'Nano IPS panel. Certified NVIDIA G-SYNC Compatible with AMD FreeSync Premium and '
                    'VESA DisplayHDR 400 support.'
                ),
                'specifications': (
                    "Screen Size: 27 Inch QHD (2560 x 1440)\n"
                    "Panel Type: Nano IPS (DCI-P3 98%)\n"
                    "Refresh Rate: 165Hz (Overclockable to 180Hz)\n"
                    "Response Time: 1ms (GtG)\n"
                    "Adaptive Sync: G-SYNC Compatible & FreeSync Premium\n"
                    "Ergonomics: Height, Pivot, Tilt Adjustable"
                ),
            },
            {
                'name': 'Logitech G PRO X Superlight 2 Wireless Gaming Mouse',
                'slug': 'logitech-g-pro-x-superlight-2',
                'category': categories['gaming-mice'],
                'brand': brands['logitech-g'],
                'sku': 'LOG-910-006628',
                'price': Decimal('139.00'),
                'original_price': Decimal('159.00'),
                'discount_percent': 0,
                'stock': 30,
                'is_featured': True,
                'sales_count': 35,
                'accent': '#06b6d4',
                'short_specs': '60g Ultra-Lightweight • HERO 2 32K Sensor • LIGHTFORCE Hybrid Switches',
                'description': (
                    'Co-designed with world-champion esports pros, the PRO X SUPERLIGHT 2 weighs just 60 grams '
                    'and features LIGHTFORCE hybrid optical-mechanical switches, the HERO 2 32,000 DPI sensor, '
                    'and 2000Hz LIGHTSPEED wireless polling.'
                ),
                'specifications': (
                    "Sensor: HERO 2 Optical (100 - 32,000 DPI)\n"
                    "Weight: 60 g\n"
                    "Switches: LIGHTFORCE Hybrid Optical-Mechanical\n"
                    "Max Report Rate: 2000 Hz (0.5ms)\n"
                    "Battery Life: Up to 95 Hours\n"
                    "Charging: USB-C & POWERPLAY Compatible"
                ),
            },
            {
                'name': 'Samsung 990 PRO 2TB PCIe 4.0 NVMe M.2 SSD',
                'slug': 'samsung-990-pro-2tb-nvme-ssd',
                'category': categories['ssd-storage'],
                'brand': brands['samsung'],
                'sku': 'MZ-V9P2T0BW',
                'price': Decimal('169.00'),
                'original_price': Decimal('199.00'),
                'discount_percent': 0,
                'stock': 25,
                'is_featured': False,
                'sales_count': 31,
                'accent': '#10b981',
                'short_specs': '2TB Capacity • 7,450 MB/s Read • 6,900 MB/s Write • PCIe Gen 4x4',
                'description': (
                    'Reach near-maximum PCIe 4.0 performance with sequential read speeds up to 7,450 MB/s '
                    'and write speeds up to 6,900 MB/s. Ideal for DirectStorage gaming, 3D rendering, and '
                    'heavy workstation workloads.'
                ),
                'specifications': (
                    "Capacity: 2 TB (2000 GB)\n"
                    "Form Factor: M.2 2280\n"
                    "Interface: PCIe Gen 4.0 x4, NVMe 2.0\n"
                    "Sequential Read: Up to 7,450 MB/s\n"
                    "Sequential Write: Up to 6,900 MB/s\n"
                    "DRAM Cache: 2GB Low Power DDR4"
                ),
            },
            {
                'name': 'HyperX Cloud III Wireless Gaming Headset',
                'slug': 'hyperx-cloud-iii-wireless-headset',
                'category': categories['headphones'],
                'brand': brands['hyperx'],
                'sku': 'HX-CL3W-BK',
                'price': Decimal('129.00'),
                'original_price': Decimal('149.99'),
                'discount_percent': 0,
                'stock': 18,
                'is_featured': False,
                'sales_count': 19,
                'accent': '#e11d48',
                'short_specs': 'Up to 120h Battery • Angled 53mm Drivers • DTS Headphone:X Spatial Audio',
                'description': (
                    'Building on the legendary Cloud II comfort, the HyperX Cloud III Wireless offers up to '
                    '120 hours of battery life, retuned 53mm angled drivers, and a crystal-clear 10mm microphone '
                    'with built-in mesh pop filter.'
                ),
                'specifications': (
                    "Driver: Dynamic 53mm with Neodymium magnets\n"
                    "Battery Life: Up to 120 hours\n"
                    "Wireless Range: Up to 20 meters (2.4GHz)\n"
                    "Spatial Audio: DTS Headphone:X\n"
                    "Frame Type: Aluminum & Steel headband\n"
                    "Microphone: Detachable 10mm noise-cancelling with LED mute indicator"
                ),
            },
            {
                'name': 'ASUS ROG Azoth 75% Wireless Custom Mechanical Keyboard',
                'slug': 'asus-rog-azoth-75-wireless-keyboard',
                'category': categories['keyboards'],
                'brand': brands['asus-rog'],
                'sku': 'ROG-AZOTH-NX-RED',
                'price': Decimal('219.00'),
                'original_price': Decimal('249.00'),
                'discount_percent': 0,
                'stock': 11,
                'is_featured': False,
                'sales_count': 12,
                'accent': '#6366f1',
                'short_specs': '75% Gasket Mount • 2" OLED Display • Hot-Swappable ROG NX Switches',
                'description': (
                    'Enthusiast-grade custom mechanical keyboard featuring a silicone gasket mount with '
                    'three-layer dampening foam, a 2-inch OLED smart screen, tri-mode connectivity, '
                    'and factory-lubed hot-swappable ROG NX mechanical switches.'
                ),
                'specifications': (
                    "Layout: 75% Compact Form Factor\n"
                    "Mount Style: Silicone Gasket Mount with 3-Layer Foam\n"
                    "Switches: Hot-Swappable Pre-lubed ROG NX Red\n"
                    "Display: 2-inch OLED Panel + 3-way Control Knob\n"
                    "Connectivity: 2.4GHz SpeedNova, Bluetooth 5.1, Wired USB-C\n"
                    "Keycaps: ROG PBT Doubleshot"
                ),
            },
            {
                'name': 'Samsung Odyssey G7 28" 4K UHD 144Hz IPS Gaming Monitor',
                'slug': 'samsung-odyssey-g7-28-4k-144hz',
                'category': categories['monitors'],
                'brand': brands['samsung'],
                'sku': 'LS28BG702EEXXY',
                'price': Decimal('469.00'),
                'original_price': Decimal('549.00'),
                'discount_percent': 0,
                'stock': 8,
                'is_featured': False,
                'sales_count': 15,
                'accent': '#3b82f6',
                'short_specs': '28" 4K UHD (3840x2160) • 144Hz IPS • HDMI 2.1 • Smart TV Hub',
                'description': (
                    'Ultra-sharp 4K UHD resolution meets 144Hz IPS responsiveness. Equipped with dual '
                    'HDMI 2.1 ports, 1ms GtG response time, and DisplayHDR 400 for lifelike contrast.'
                ),
                'specifications': (
                    "Resolution: 4K UHD (3840 x 2160)\n"
                    "Screen Size: 28 Inch Fast IPS\n"
                    "Refresh Rate: 144Hz\n"
                    "Response Time: 1ms (GtG)\n"
                    "Ports: 2x HDMI 2.1, 1x DisplayPort 1.4, Ethernet, USB Hub\n"
                    "HDR: VESA DisplayHDR 400"
                ),
            },
        ]

        for pdata in new_products:
            img_path = generate_product_image(
                f"{pdata['slug']}.jpg",
                pdata['name'],
                pdata['brand'].name,
                pdata['accent']
            )
            Product.objects.update_or_create(
                slug=pdata['slug'],
                defaults={
                    'name': pdata['name'],
                    'category': pdata['category'],
                    'brand': pdata['brand'],
                    'sku': pdata['sku'],
                    'price': pdata['price'],
                    'original_price': pdata['original_price'],
                    'discount_percent': pdata['discount_percent'],
                    'stock': pdata['stock'],
                    'available': True,
                    'is_featured': pdata['is_featured'],
                    'sales_count': pdata['sales_count'],
                    'short_specs': pdata['short_specs'],
                    'description': pdata['description'],
                    'specifications': pdata['specifications'],
                    'image': img_path,
                }
            )

        # 5. Active Discount Campaigns
        disc1, _ = Discount.objects.update_or_create(
            name='Pro Audio & Peripherals Deal',
            defaults={
                'description': '10% additional discount on gaming headphones and audio accessories.',
                'discount_type': 'percentage',
                'value': Decimal('10.00'),
                'start_date': now - timedelta(days=5),
                'end_date': now + timedelta(days=60),
                'is_active': True,
            }
        )
        disc1.categories.set([categories['headphones']])

        disc2, _ = Discount.objects.update_or_create(
            name='Next-Gen GPU Instant Rebate',
            defaults={
                'description': '$20 instant savings on flagship Graphics Cards.',
                'discount_type': 'fixed',
                'value': Decimal('20.00'),
                'start_date': now - timedelta(days=2),
                'end_date': now + timedelta(days=45),
                'is_active': True,
            }
        )
        disc2.categories.set([categories['graphics-cards']])

        # 6. Promotional Codes
        PromoCode.objects.update_or_create(
            code='PCSHOP10',
            defaults={
                'description': '10% off any order over $30',
                'discount_type': 'percentage',
                'discount_value': Decimal('10.00'),
                'min_order_amount': Decimal('30.00'),
                'usage_limit': 500,
                'valid_from': now - timedelta(days=10),
                'valid_until': now + timedelta(days=90),
                'is_active': True,
            }
        )
        PromoCode.objects.update_or_create(
            code='GAMER25',
            defaults={
                'description': '$25 off orders over $200',
                'discount_type': 'fixed',
                'discount_value': Decimal('25.00'),
                'min_order_amount': Decimal('200.00'),
                'usage_limit': 100,
                'valid_from': now - timedelta(days=5),
                'valid_until': now + timedelta(days=60),
                'is_active': True,
            }
        )
        PromoCode.objects.update_or_create(
            code='EXPIRED50',
            defaults={
                'description': 'Expired test promo code',
                'discount_type': 'percentage',
                'discount_value': Decimal('50.00'),
                'min_order_amount': Decimal('10.00'),
                'usage_limit': 10,
                'valid_from': now - timedelta(days=60),
                'valid_until': now - timedelta(days=5),
                'is_active': True,
            }
        )

        # 7. Seed sample Reviews & Orders if none exist yet
        rasul_user = User.objects.filter(username='rasul').first() or User.objects.first()
        luffy_user = User.objects.filter(username='luffy').first() or rasul_user
        all_products = list(Product.objects.all())

        if Review.objects.count() == 0 and rasul_user and all_products:
            sample_reviews = [
                (all_products[0], rasul_user, 'Fantastic positional audio and comfort!',
                 'Used this headset for competitive CS2 and Valorant. The 50mm drivers are super clear and the ear pads stay cool even after 4 hours.', 5),
                (all_products[1], luffy_user, 'Best low-profile TKL keyboard for the price',
                 'The Kailh red low-profile switches feel super crisp and fast. RGB modes work without bloated software.', 5),
            ]
            if len(all_products) > 3:
                sample_reviews.append(
                    (all_products[2], rasul_user, 'Runs every game at 1440p Ultra effortlessly',
                     'Upgraded from an RTX 3060 and the frame rate jump is massive. Whisper quiet cooling under full load.', 5)
                )
                sample_reviews.append(
                    (all_products[3], luffy_user, 'Unbeatable gaming CPU!',
                     '3D V-Cache makes a huge difference in simulation and open-world games. Temps are very manageable with a 240mm AIO.', 5)
                )
            for prod, usr, title, body, rating in sample_reviews:
                Review.objects.create(
                    product=prod, user=usr, title=title, body=body, rating=rating, is_approved=True
                )

        if Order.objects.count() == 0 and rasul_user and len(all_products) >= 4:
            promo = PromoCode.objects.filter(code='PCSHOP10').first()
            orders_seed = [
                (rasul_user, 'Rasul', 'Abdikerimov', 'rasulabdikerimov85@gmail.com', '+998901234567',
                 'Amir Temur Avenue 108', 'Tashkent', '100084', 'delivered', 'paid',
                 [(all_products[0], 1), (all_products[1], 1)], promo),
                (luffy_user, 'Monkey D.', 'Luffy', 'luffy@pcshop.uz', '+998935551122',
                 'Mustaqillik Street 45', 'Nukus', '230100', 'shipped', 'paid',
                 [(all_products[3], 1)], None),
                (rasul_user, 'Rasul', 'Abdikerimov', 'rasulabdikerimov85@gmail.com', '+998901234567',
                 'Amir Temur Avenue 108', 'Tashkent', '100084', 'pending', 'pending',
                 [(all_products[2], 1)], None),
            ]
            for usr, fn, ln, em, ph, addr, city, postal, st, pst, items_spec, prm in orders_seed:
                subtotal = sum(p.get_final_price() * q for p, q in items_spec)
                disc_amt = prm.calculate_discount(subtotal) if prm else Decimal('0.00')
                total = max(subtotal - disc_amt, Decimal('0.00'))
                order = Order.objects.create(
                    user=usr, first_name=fn, last_name=ln, email=em, phone=ph,
                    address=addr, city=city, postal_code=postal,
                    status=st, payment_status=pst, payment_method='cod',
                    subtotal=subtotal, discount_amount=disc_amt, promo_code=prm,
                    total_amount=total,
                )
                for p, q in items_spec:
                    OrderItem.objects.create(
                        order=order, product=p, product_name=p.name,
                        price=p.get_final_price(), original_unit_price=p.get_base_price(),
                        quantity=q
                    )
                if prm:
                    prm.used_count += 1
                    prm.save(update_fields=['used_count'])

        self.stdout.write(self.style.SUCCESS(
            f"Catalog seeded successfully: {Category.objects.count()} categories, "
            f"{Brand.objects.count()} brands, {Product.objects.count()} products, "
            f"{Discount.objects.count()} discounts, {PromoCode.objects.count()} promo codes, "
            f"{Order.objects.count()} orders."
        ))

