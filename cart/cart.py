from decimal import Decimal
from django.conf import settings
from shop.models import Product
from .models import PromoCode


class Cart(object):

    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_ID)
        if not cart:
            cart = self.session[settings.CART_SESSION_ID] = {}
        self.cart = cart
        self.promo_code_id = self.session.get(getattr(settings, 'PROMO_SESSION_ID', 'promo_code_id'))

    def __iter__(self):
        product_ids = list(self.cart.keys())
        products = Product.objects.filter(id__in=product_ids).select_related('category', 'brand')
        product_map = {str(p.id): p for p in products}

        for pid, raw_item in list(self.cart.items()):
            product = product_map.get(str(pid))
            if not product:
                continue
            item = raw_item.copy()
            item['product'] = product
            # Always compute live server price (never trust client/stale session price)
            unit_price = product.get_final_price()
            original_unit_price = product.get_base_price()
            quantity = max(1, int(item.get('quantity', 1)))
            item['quantity'] = quantity
            item['price'] = unit_price
            item['original_price'] = original_unit_price
            item['total_price'] = unit_price * quantity
            item['is_available'] = product.in_stock and product.stock >= quantity
            yield item

    def __len__(self):
        return sum(max(0, int(item.get('quantity', 0))) for item in self.cart.values())

    def add(self, product, quantity=1, update_quantity=False):
        product_id = str(product.id)
        quantity = max(1, int(quantity))
        if product_id not in self.cart:
            self.cart[product_id] = {
                'quantity': 0,
                'price': str(product.get_final_price())
            }
        if update_quantity:
            new_qty = quantity
        else:
            new_qty = self.cart[product_id]['quantity'] + quantity

        if product.stock > 0:
            new_qty = min(new_qty, product.stock)

        self.cart[product_id]['quantity'] = new_qty
        self.cart[product_id]['price'] = str(product.get_final_price())
        self.save()

    def save(self):
        self.session.modified = True

    def remove(self, product):
        product_id = str(product.id if hasattr(product, 'id') else product)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def get_subtotal(self):
        product_ids = list(self.cart.keys())
        products = Product.objects.filter(id__in=product_ids)
        product_map = {str(p.id): p for p in products}
        subtotal = Decimal('0.00')
        for pid, item in self.cart.items():
            product = product_map.get(str(pid))
            if product and product.available:
                qty = max(0, int(item.get('quantity', 0)))
                subtotal += product.get_final_price() * qty
        return subtotal

    def get_product_savings(self):
        product_ids = list(self.cart.keys())
        products = Product.objects.filter(id__in=product_ids)
        product_map = {str(p.id): p for p in products}
        savings = Decimal('0.00')
        for pid, item in self.cart.items():
            product = product_map.get(str(pid))
            if product and product.available and product.has_discount:
                qty = max(0, int(item.get('quantity', 0)))
                savings += (product.get_base_price() - product.get_final_price()) * qty
        return savings

    @property
    def promo_code(self):
        if not self.promo_code_id:
            return None
        try:
            promo = PromoCode.objects.get(id=self.promo_code_id)
            is_ok, _ = promo.validate_for_cart(self.get_subtotal())
            if is_ok:
                return promo
        except PromoCode.DoesNotExist:
            pass
        return None

    def get_discount(self):
        promo = self.promo_code
        if promo:
            return promo.calculate_discount(self.get_subtotal())
        return Decimal('0.00')

    def get_total_price(self):
        subtotal = self.get_subtotal()
        discount = self.get_discount()
        return max(subtotal - discount, Decimal('0.00'))

    def clear(self):
        if settings.CART_SESSION_ID in self.session:
            del self.session[settings.CART_SESSION_ID]
        promo_key = getattr(settings, 'PROMO_SESSION_ID', 'promo_code_id')
        if promo_key in self.session:
            del self.session[promo_key]
        self.save()
