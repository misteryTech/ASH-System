import re

from django.db import transaction

from .models import Product, ProductPriceHistory
from .validators import normalize_name

PRICE_FIELDS = [
    "cost_price",
    "wholesale_price",
    "retail_price",
    "suggested_retail_price",
    "selling_price",
    "discounted_price",
    "minimum_selling_price",
]


def _code_from(text, length):
    letters = re.sub(r"[^A-Za-z0-9]", "", text or "").upper()
    if not letters:
        return "GEN"
    return letters[:length].ljust(length, "X")


def generate_sku(category, brand=None, attempts=20):
    """Build a unique SKU like BOLT-BOS-00001. Retries on collision since
    MySQL has no native sequence object to reserve a number atomically."""
    category_code = _code_from(category.name if category else "", 4)
    brand_code = _code_from(brand.name if brand else "GEN", 3)
    prefix = f"{category_code}-{brand_code}-"

    existing_max = 0
    for sku in Product.objects.filter(sku__startswith=prefix).values_list("sku", flat=True):
        match = re.match(rf"^{re.escape(prefix)}(\d+)$", sku)
        if match:
            existing_max = max(existing_max, int(match.group(1)))

    for i in range(1, attempts + 1):
        candidate = f"{prefix}{existing_max + i:05d}"
        if not Product.objects.filter(sku=candidate).exists():
            return candidate

    raise RuntimeError("Could not generate a unique SKU after multiple attempts.")


def find_possible_duplicates(name, category=None, brand=None, size="", exclude_pk=None):
    """Non-blocking 'possible duplicate' search on normalized composite
    identity (name + category + brand [+ size]). Exact identifiers (SKU,
    barcode, OEM/part number) are enforced separately via hard DB constraints
    and regular form validation — this is a softer, reviewable warning."""
    normalized = normalize_name(name)
    if not normalized:
        return Product.objects.none()

    queryset = Product.objects.filter(normalized_name=normalized, is_active=True)
    if category is not None:
        queryset = queryset.filter(category=category)
    if brand is not None:
        queryset = queryset.filter(brand=brand)
    if size:
        queryset = queryset.filter(size__iexact=size)
    if exclude_pk:
        queryset = queryset.exclude(pk=exclude_pk)
    return queryset


@transaction.atomic
def save_product_with_price_history(product, user, price_snapshot_before=None):
    """Save a product, logging any price-field changes to ProductPriceHistory.
    `price_snapshot_before` is a dict of {field_name: old_value} captured by
    the caller before mutating the in-memory instance (None for new products).
    """
    is_new = product.pk is None
    product.updated_by = user
    if is_new:
        product.created_by = user
    product.full_clean()
    product.save()

    if is_new:
        for field_name in PRICE_FIELDS:
            new_value = getattr(product, field_name)
            if new_value:
                ProductPriceHistory.objects.create(
                    product=product, field_name=field_name, old_price=None, new_price=new_value, changed_by=user
                )
    elif price_snapshot_before:
        for field_name in PRICE_FIELDS:
            old_value = price_snapshot_before.get(field_name)
            new_value = getattr(product, field_name)
            if old_value != new_value:
                ProductPriceHistory.objects.create(
                    product=product,
                    field_name=field_name,
                    old_price=old_value,
                    new_price=new_value,
                    changed_by=user,
                )

    return product
