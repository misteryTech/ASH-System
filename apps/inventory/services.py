import re

from django.db import transaction

from .models import Brand, Category, InventoryActivityLog, Manufacturer, Product, ProductPriceHistory
from .utils import barcode_value_for
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

# Fields tracked by the inventory activity log when a product is edited.
# Deliberately narrower than every Product field — spec section 6's list
# (name/SKU/barcode/category/brand/manufacturer/part & OEM number/color/
# size/price/reorder level/status) plus PRICE_FIELDS above.
TRACKED_PRODUCT_FIELDS = (
    ["name", "sku", "barcode_number", "category", "brand", "manufacturer",
     "part_number", "oem_number", "color", "size", "reorder_level", "is_active"]
    + PRICE_FIELDS
)
_FK_DISPLAY_MODELS = {"category": Category, "brand": Brand, "manufacturer": Manufacturer}


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


def _get_client_ip(request):
    if request is None:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def record_activity(
    *,
    user,
    action,
    product=None,
    quantity_before=None,
    quantity_changed=None,
    quantity_after=None,
    reference_type="",
    reference_id="",
    field_name="",
    previous_value="",
    new_value="",
    remarks="",
    activity_date=None,
    request=None,
):
    """Create one immutable InventoryActivityLog row. Called from inside the
    same transaction.atomic() block as the operation it records, so a failed
    operation rolls back its log entry too (no false-positive audit rows).
    `activity_date` is the business date the action pertains to (e.g. the
    date stock was actually received) — leave it None for actions with no
    such date; the log list falls back to created_at's date for those."""
    return InventoryActivityLog.objects.create(
        user=user,
        action=action,
        product=product,
        product_name_snapshot=product.name if product else "",
        sku_snapshot=product.sku if product else "",
        barcode_snapshot=barcode_value_for(product) if product else "",
        quantity_before=quantity_before,
        quantity_changed=quantity_changed,
        quantity_after=quantity_after,
        reference_type=reference_type,
        reference_id=reference_id,
        field_name=field_name,
        previous_value=previous_value or "",
        new_value=new_value or "",
        remarks=remarks,
        activity_date=activity_date,
        ip_address=_get_client_ip(request),
    )


def add_stock(*, product, quantity, date_added, user, remarks="", request=None):
    """Add `quantity` units to product.quantity_on_hand and record a dated,
    logged STOCK_ADDED activity row — the only sanctioned way to increase
    stock (spec: no silent inventory quantity changes). Atomic: if anything
    fails, neither the quantity change nor the log row is committed."""
    if quantity <= 0:
        raise ValueError("Quantity to add must be greater than zero.")

    with transaction.atomic():
        # Row-lock the product for the duration of the update so two
        # concurrent "add stock" submissions can't both read the same
        # before-quantity and silently drop one of the additions.
        locked_product = Product.objects.select_for_update().get(pk=product.pk)
        quantity_before = locked_product.quantity_on_hand
        quantity_after = quantity_before + quantity
        locked_product.quantity_on_hand = quantity_after
        locked_product.save(update_fields=["quantity_on_hand", "updated_at"])

        record_activity(
            user=user,
            action=InventoryActivityLog.Action.STOCK_ADDED,
            product=locked_product,
            quantity_before=quantity_before,
            quantity_changed=quantity,
            quantity_after=quantity_after,
            remarks=remarks,
            activity_date=date_added,
            request=request,
        )

    product.quantity_on_hand = quantity_after
    return product


def snapshot_product_fields(product):
    """Capture the tracked fields of a product before it's mutated, for
    diffing in record_product_field_changes(). FK fields are captured by id
    (via the _id attribute) so they compare cleanly against the post-save
    instance without triggering extra queries."""
    snapshot = {}
    for field_name in TRACKED_PRODUCT_FIELDS:
        if field_name in _FK_DISPLAY_MODELS:
            snapshot[field_name] = getattr(product, f"{field_name}_id")
        else:
            snapshot[field_name] = getattr(product, field_name)
    return snapshot


def _display_value(field_name, value):
    if field_name in _FK_DISPLAY_MODELS:
        if value is None:
            return ""
        obj = _FK_DISPLAY_MODELS[field_name].objects.filter(pk=value).first()
        return str(obj) if obj else f"#{value}"
    if value is None or value == "":
        return ""
    return str(value)


def record_product_field_changes(product, before, user, request=None):
    """Diff `before` (from snapshot_product_fields, captured pre-save)
    against the now-saved `product` and write one InventoryActivityLog row
    per field that actually changed. Fields with no change are skipped
    entirely — no duplicate/no-op log rows."""
    created = []
    after = snapshot_product_fields(product)

    for field_name in TRACKED_PRODUCT_FIELDS:
        old_value = before.get(field_name)
        new_value = after.get(field_name)
        if old_value == new_value:
            continue

        action = InventoryActivityLog.Action.PRODUCT_UPDATED
        if field_name == "is_active" and old_value is True and new_value is False:
            action = InventoryActivityLog.Action.PRODUCT_DEACTIVATED

        created.append(
            record_activity(
                user=user,
                action=action,
                product=product,
                field_name=field_name,
                previous_value=_display_value(field_name, old_value),
                new_value=_display_value(field_name, new_value),
                request=request,
            )
        )
    return created
