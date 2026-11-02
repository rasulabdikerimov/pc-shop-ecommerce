from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.conf import settings
from django.db import transaction
from django.http import Http404
from shop.models import Product
from .cart import Cart
from .models import PromoCode, Order, OrderItem
from .forms import CartAddProductForm, PromoCodeApplyForm, OrderCreateForm


@require_POST
def cart_add(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)

    if not product.in_stock:
        messages.error(request, f"Sorry, '{product.name}' is currently out of stock.")
        return redirect('cart:cart_detail')

    form = CartAddProductForm(request.POST)
    if form.is_valid():
        cd = form.cleaned_data
        requested_qty = cd['quantity']
        current_in_cart = cart.cart.get(str(product.id), {}).get('quantity', 0)
        target_qty = requested_qty if cd['update'] else (current_in_cart + requested_qty)

        if target_qty > product.stock:
            messages.warning(
                request,
                f"Only {product.stock} unit(s) of '{product.name}' are available in stock. Quantity adjusted."
            )

        cart.add(
            product=product,
            quantity=requested_qty,
            update_quantity=cd['update']
        )
        messages.success(request, f"Updated '{product.name}' in your shopping cart.")
    else:
        messages.error(request, "Invalid quantity selected.")

    return redirect('cart:cart_detail')


def cart_remove(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product)
    messages.info(request, f"Removed '{product.name}' from your cart.")
    return redirect('cart:cart_detail')


def cart_detail(request):
    cart = Cart(request)
    for item in cart:
        item['update_quantity_form'] = CartAddProductForm(
            initial={'quantity': item['quantity'], 'update': True}
        )
    promo_form = PromoCodeApplyForm()
    return render(
        request,
        'cart/detail.html',
        {
            'cart': cart,
            'promo_form': promo_form,
        }
    )


@require_POST
def promo_apply(request):
    cart = Cart(request)
    form = PromoCodeApplyForm(request.POST)
    promo_key = getattr(settings, 'PROMO_SESSION_ID', 'promo_code_id')

    if form.is_valid():
        code = form.cleaned_data['code'].strip().upper()
        try:
            promo = PromoCode.objects.get(code__iexact=code)
            is_valid, msg = promo.validate_for_cart(cart.get_subtotal())
            if is_valid:
                request.session[promo_key] = promo.id
                messages.success(request, f"Promo code '{promo.code}' applied: {promo.get_discount_display_label()}!")
            else:
                request.session.pop(promo_key, None)
                messages.error(request, msg)
        except PromoCode.DoesNotExist:
            request.session.pop(promo_key, None)
            messages.error(request, f"Promotional code '{code}' is invalid.")
    return redirect('cart:cart_detail')


@require_POST
def promo_remove(request):
    promo_key = getattr(settings, 'PROMO_SESSION_ID', 'promo_code_id')
    if promo_key in request.session:
        del request.session[promo_key]
        messages.info(request, "Promotional code removed.")
    return redirect('cart:cart_detail')


def checkout(request):
    cart = Cart(request)
    if len(cart) == 0:
        messages.warning(request, "Your shopping cart is empty. Please add products before checking out.")
        return redirect('cart:cart_detail')

    initial_data = {}
    if request.user.is_authenticated:
        initial_data = {
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email,
            'phone': request.user.phone_num,
            'address': request.user.address,
            'city': request.user.city or 'Tashkent',
            'postal_code': request.user.postal_code,
        }

    if request.method == 'POST':
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    cart_items = list(cart)
                    if not cart_items:
                        messages.error(request, "Your shopping cart contains no available products.")
                        return redirect('cart:cart_detail')

                    subtotal = Decimal('0.00')
                    locked_items = []

                    # Lock products to prevent race conditions and verify stock
                    for item in cart_items:
                        locked_product = Product.objects.select_for_update().get(id=item['product'].id)
                        qty = item['quantity']
                        if not locked_product.available or locked_product.stock < qty:
                            raise ValueError(
                                f"Insufficient stock for '{locked_product.name}' (Available: {locked_product.stock}, Requested: {qty})."
                            )
                        unit_price = locked_product.get_final_price()
                        orig_price = locked_product.get_base_price()
                        subtotal += unit_price * qty
                        locked_items.append((locked_product, qty, unit_price, orig_price))

                    # Validate and lock promotional code if present
                    promo_obj = None
                    discount_amount = Decimal('0.00')
                    promo_id = request.session.get(getattr(settings, 'PROMO_SESSION_ID', 'promo_code_id'))
                    if promo_id:
                        try:
                            locked_promo = PromoCode.objects.select_for_update().get(id=promo_id)
                            is_ok, err_msg = locked_promo.validate_for_cart(subtotal)
                            if not is_ok:
                                raise ValueError(err_msg)
                            discount_amount = locked_promo.calculate_discount(subtotal)
                            locked_promo.used_count += 1
                            locked_promo.save(update_fields=['used_count'])
                            promo_obj = locked_promo
                        except PromoCode.DoesNotExist:
                            pass

                    total_amount = max(subtotal - discount_amount, Decimal('0.00'))

                    order = form.save(commit=False)
                    if request.user.is_authenticated:
                        order.user = request.user
                    order.status = 'pending'
                    # Never simulate a successful real online payment
                    order.payment_status = 'pending'
                    order.subtotal = subtotal
                    order.discount_amount = discount_amount
                    order.promo_code = promo_obj
                    order.total_amount = total_amount
                    order.save()

                    for locked_product, qty, unit_price, orig_price in locked_items:
                        OrderItem.objects.create(
                            order=order,
                            product=locked_product,
                            product_name=locked_product.name,
                            price=unit_price,
                            original_unit_price=orig_price,
                            quantity=qty
                        )
                        locked_product.stock -= qty
                        locked_product.sales_count += qty
                        locked_product.save(update_fields=['stock', 'sales_count'])

                    cart.clear()
                    request.session['last_order_number'] = order.order_number
                    messages.success(request, f"Order #{order.order_number} has been placed successfully!")
                    return redirect('cart:order_success', order_number=order.order_number)

            except ValueError as exc:
                messages.error(request, str(exc))
                return redirect('cart:cart_detail')
    else:
        form = OrderCreateForm(initial=initial_data)

    return render(
        request,
        'cart/checkout.html',
        {
            'cart': cart,
            'form': form,
            'promo_form': PromoCodeApplyForm(),
        }
    )


def order_success(request, order_number):
    order = get_object_or_404(Order.objects.prefetch_related('items__product'), order_number=order_number)
    # Enforce strict order ownership check
    if order.user_id is not None:
        if not request.user.is_authenticated or (request.user.id != order.user_id and not request.user.is_staff):
            raise Http404("Order not found.")
    else:
        if request.session.get('last_order_number') != order.order_number and not (request.user.is_authenticated and request.user.is_staff):
            raise Http404("Order not found.")

    return render(request, 'cart/order_success.html', {'order': order})
