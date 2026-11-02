from django.utils import timezone
from .models import Category


def shop_context(request):
    """Global template context for navigation categories, wishlist state, and active promos."""
    categories = Category.objects.all()
    wishlist_count = 0
    wishlist_product_ids = set()

    if request.user.is_authenticated:
        try:
            from .models import Wishlist
            wishlist_qs = Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True)
            wishlist_product_ids = set(wishlist_qs)
            wishlist_count = len(wishlist_product_ids)
        except Exception:
            pass

    active_promo = None
    try:
        from cart.models import PromoCode
        now = timezone.now()
        active_promo = (
            PromoCode.objects.filter(is_active=True, valid_from__lte=now, valid_until__gte=now)
            .order_by('-discount_value')
            .first()
        )
    except Exception:
        pass

    return {
        'global_categories': categories,
        'wishlist_count': wishlist_count,
        'wishlist_product_ids': wishlist_product_ids,
        'featured_promo': active_promo,
    }

