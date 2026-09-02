import calendar
from datetime import date

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.db.models.functions import Coalesce, TruncDate
from django.shortcuts import get_object_or_404, redirect, render
from django.http import HttpResponse
from django.utils.dateparse import parse_date

from apps.accounts.models import User

from .forms import (
    BrandForm,
    CategoryForm,
    ManufacturerForm,
    ProductAttributeValueFormSet,
    ProductCompatibilityFormSet,
    ProductForm,
    ProductImageForm,
    StockAddForm,
    SupplierForm,
)
from .models import Brand, Category, InventoryActivityLog, Manufacturer, Product, ProductImage, Supplier
from .permissions import inventory_log_view_required, inventory_manage_required, inventory_view_required
from .reporting import format_period_label, get_quick_range, month_range
from .services import (
    PRICE_FIELDS,
    add_stock,
    find_possible_duplicates,
    record_activity,
    record_product_field_changes,
    save_product_with_price_history,
    snapshot_product_fields,
)
from .utils import barcode_value_for, generate_barcode_png

# ---------- Lookup CRUD helpers (Category / Brand / Manufacturer / Supplier) ----------
# Shared logic for the four simple lookup tables so each concrete view below
# stays a thin, named wrapper (keeps named URLs / templates per model while
# avoiding four copies of identical list/edit/toggle logic).


def _lookup_list(request, model, form_class, template_name, url_name):
    query = request.GET.get("q", "").strip()
    items = model.objects.all()
    if query:
        items = items.filter(name__icontains=query)

    if request.method == "POST":
        form = form_class(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f"{model._meta.verbose_name} created successfully.")
            return redirect(url_name)
        messages.error(request, "Please correct the errors below.")
    else:
        form = form_class()

    return render(request, template_name, {"items": items, "form": form, "query": query})


def _lookup_edit(request, model, form_class, pk, template_name, url_name):
    obj = get_object_or_404(model, pk=pk)
    if request.method == "POST":
        form = form_class(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, f"{model._meta.verbose_name} updated successfully.")
            return redirect(url_name)
        messages.error(request, "Please correct the errors below.")
    else:
        form = form_class(instance=obj)
    return render(request, template_name, {"form": form, "object": obj})


def _lookup_toggle(request, model, pk, url_name):
    obj = get_object_or_404(model, pk=pk)
    if request.method == "POST":
        obj.is_active = not obj.is_active
        obj.save(update_fields=["is_active"])
        status = "activated" if obj.is_active else "deactivated"
        messages.success(request, f"'{obj.name}' has been {status}.")
    return redirect(url_name)


@inventory_manage_required
def category_list(request):
    return _lookup_list(request, Category, CategoryForm, "inventory/category_list.html", "inventory:category_list")


@inventory_manage_required
def category_edit(request, pk):
    return _lookup_edit(
        request, Category, CategoryForm, pk, "inventory/category_edit.html", "inventory:category_list"
    )


@inventory_manage_required
def category_toggle(request, pk):
    return _lookup_toggle(request, Category, pk, "inventory:category_list")


@inventory_manage_required
def brand_list(request):
    return _lookup_list(request, Brand, BrandForm, "inventory/brand_list.html", "inventory:brand_list")


@inventory_manage_required
def brand_edit(request, pk):
    return _lookup_edit(request, Brand, BrandForm, pk, "inventory/brand_edit.html", "inventory:brand_list")


@inventory_manage_required
def brand_toggle(request, pk):
    return _lookup_toggle(request, Brand, pk, "inventory:brand_list")


@inventory_manage_required
def manufacturer_list(request):
    return _lookup_list(
        request, Manufacturer, ManufacturerForm, "inventory/manufacturer_list.html", "inventory:manufacturer_list"
    )


@inventory_manage_required
def manufacturer_edit(request, pk):
    return _lookup_edit(
        request, Manufacturer, ManufacturerForm, pk, "inventory/manufacturer_edit.html", "inventory:manufacturer_list"
    )


@inventory_manage_required
def manufacturer_toggle(request, pk):
    return _lookup_toggle(request, Manufacturer, pk, "inventory:manufacturer_list")


@inventory_manage_required
def supplier_list(request):
    return _lookup_list(request, Supplier, SupplierForm, "inventory/supplier_list.html", "inventory:supplier_list")


@inventory_manage_required
def supplier_edit(request, pk):
    return _lookup_edit(request, Supplier, SupplierForm, pk, "inventory/supplier_edit.html", "inventory:supplier_list")


@inventory_manage_required
def supplier_toggle(request, pk):
    return _lookup_toggle(request, Supplier, pk, "inventory:supplier_list")


# ---------- Products ----------


@inventory_view_required
def product_list(request):
    query = request.GET.get("q", "").strip()
    category_filter = request.GET.get("category", "").strip()
    status_filter = request.GET.get("status", "").strip()

    products = Product.objects.select_related("category", "brand", "manufacturer")
    if query:
        products = products.filter(
            Q(name__icontains=query)
            | Q(sku__icontains=query)
            | Q(barcode_number__icontains=query)
            | Q(part_number__icontains=query)
            | Q(oem_number__icontains=query)
        )
    if category_filter:
        products = products.filter(category_id=category_filter)
    if status_filter == "active":
        products = products.filter(is_active=True)
    elif status_filter == "inactive":
        products = products.filter(is_active=False)

    context = {
        "products": products,
        "query": query,
        "category_filter": category_filter,
        "status_filter": status_filter,
        "categories": Category.objects.filter(is_active=True),
    }
    return render(request, "inventory/product_list.html", context)


@inventory_manage_required
def product_create(request):
    if request.method != "POST":
        form = ProductForm()
        compat_formset = ProductCompatibilityFormSet(prefix="compat")
        attr_formset = ProductAttributeValueFormSet(prefix="attr")
        return render(
            request,
            "inventory/product_form.html",
            {"form": form, "compat_formset": compat_formset, "attr_formset": attr_formset, "is_edit": False},
        )

    form = ProductForm(request.POST)
    product = None
    possible_duplicates = None

    if form.is_valid():
        product = form.save(commit=False)
        if not form.cleaned_data.get("confirm_duplicate"):
            duplicates = find_possible_duplicates(product.name, product.category, product.brand, product.size)
            if duplicates.exists():
                possible_duplicates = duplicates

    formset_instance = product if (product is not None and possible_duplicates is None) else Product()
    compat_formset = ProductCompatibilityFormSet(request.POST, instance=formset_instance, prefix="compat")
    attr_formset = ProductAttributeValueFormSet(request.POST, instance=formset_instance, prefix="attr")

    if product is not None and possible_duplicates is None:
        if compat_formset.is_valid() and attr_formset.is_valid():
            with transaction.atomic():
                save_product_with_price_history(product, request.user)
                compat_formset.instance = product
                compat_formset.save()
                attr_formset.instance = product
                attr_formset.save()
                record_activity(
                    user=request.user,
                    action=InventoryActivityLog.Action.PRODUCT_CREATED,
                    product=product,
                    request=request,
                )
            messages.success(request, f"Product '{product.name}' created successfully.")
            return redirect("inventory:product_detail", pk=product.pk)
        messages.error(request, "Please correct the errors below.")
    elif product is None:
        messages.error(request, "Please correct the errors below.")

    return render(
        request,
        "inventory/product_form.html",
        {
            "form": form,
            "compat_formset": compat_formset,
            "attr_formset": attr_formset,
            "possible_duplicates": possible_duplicates,
            "is_edit": False,
        },
    )


@inventory_manage_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if request.method != "POST":
        form = ProductForm(instance=product)
        compat_formset = ProductCompatibilityFormSet(instance=product, prefix="compat")
        attr_formset = ProductAttributeValueFormSet(instance=product, prefix="attr")
        return render(
            request,
            "inventory/product_form.html",
            {
                "form": form,
                "compat_formset": compat_formset,
                "attr_formset": attr_formset,
                "is_edit": True,
                "product": product,
            },
        )

    price_snapshot = Product.objects.filter(pk=product.pk).values(*PRICE_FIELDS).first()
    field_snapshot = snapshot_product_fields(product)
    form = ProductForm(request.POST, instance=product)

    if form.is_valid():
        updated_product = form.save(commit=False)
        compat_formset = ProductCompatibilityFormSet(request.POST, instance=updated_product, prefix="compat")
        attr_formset = ProductAttributeValueFormSet(request.POST, instance=updated_product, prefix="attr")

        if compat_formset.is_valid() and attr_formset.is_valid():
            with transaction.atomic():
                save_product_with_price_history(updated_product, request.user, price_snapshot_before=price_snapshot)
                compat_formset.save()
                attr_formset.save()
                record_product_field_changes(updated_product, field_snapshot, request.user, request=request)
            messages.success(request, f"Product '{updated_product.name}' updated successfully.")
            return redirect("inventory:product_detail", pk=updated_product.pk)
        messages.error(request, "Please correct the errors below.")
    else:
        compat_formset = ProductCompatibilityFormSet(request.POST, instance=product, prefix="compat")
        attr_formset = ProductAttributeValueFormSet(request.POST, instance=product, prefix="attr")
        messages.error(request, "Please correct the errors below.")

    return render(
        request,
        "inventory/product_form.html",
        {
            "form": form,
            "compat_formset": compat_formset,
            "attr_formset": attr_formset,
            "is_edit": True,
            "product": product,
        },
    )


@inventory_view_required
def product_detail(request, pk):
    product = get_object_or_404(
        Product.objects.select_related("category", "brand", "manufacturer").prefetch_related(
            "images",
            "compatibilities",
            "attribute_values__attribute",
            "supplier_links__supplier",
            "price_history__changed_by",
        ),
        pk=pk,
    )
    stock_history = product.activity_logs.filter(
        action__in=[InventoryActivityLog.Action.STOCK_ADDED, InventoryActivityLog.Action.STOCK_RECEIVED]
    ).annotate(effective_date=Coalesce("activity_date", TruncDate("created_at"))).order_by("-effective_date", "-created_at")[:20]

    context = {
        "product": product,
        "image_form": ProductImageForm(),
        "stock_add_form": StockAddForm(initial={"date_added": date.today()}),
        "stock_history": stock_history,
    }
    return render(request, "inventory/product_detail.html", context)


@inventory_manage_required
def product_add_stock(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        form = StockAddForm(request.POST)
        if form.is_valid():
            add_stock(
                product=product,
                quantity=form.cleaned_data["quantity"],
                date_added=form.cleaned_data["date_added"],
                user=request.user,
                remarks=form.cleaned_data["remarks"],
                request=request,
            )
            messages.success(
                request,
                f"Added {form.cleaned_data['quantity']} unit(s) to '{product.name}' "
                f"(dated {form.cleaned_data['date_added']:%B %d, %Y}).",
            )
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
    return redirect("inventory:product_detail", pk=pk)


@inventory_manage_required
def product_image_upload(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        form = ProductImageForm(request.POST, request.FILES)
        if form.is_valid():
            is_first = not product.images.exists()
            image = ProductImage.objects.create(
                product=product,
                image=form.cleaned_data["image"],
                is_primary=is_first or form.cleaned_data["is_primary"],
            )
            if image.is_primary:
                product.images.exclude(pk=image.pk).update(is_primary=False)
            messages.success(request, "Image uploaded successfully.")
        else:
            for error in form.errors.get("image", []):
                messages.error(request, error)
    return redirect("inventory:product_detail", pk=pk)


@inventory_manage_required
def product_image_delete(request, pk, image_id):
    product = get_object_or_404(Product, pk=pk)
    image = get_object_or_404(ProductImage, pk=image_id, product=product)
    if request.method == "POST":
        was_primary = image.is_primary
        image.delete()
        if was_primary:
            next_image = product.images.first()
            if next_image:
                next_image.is_primary = True
                next_image.save(update_fields=["is_primary"])
        messages.success(request, "Image deleted successfully.")
    return redirect("inventory:product_detail", pk=pk)


@inventory_manage_required
def product_image_set_primary(request, pk, image_id):
    product = get_object_or_404(Product, pk=pk)
    image = get_object_or_404(ProductImage, pk=image_id, product=product)
    if request.method == "POST":
        product.images.exclude(pk=image.pk).update(is_primary=False)
        image.is_primary = True
        image.save(update_fields=["is_primary"])
        messages.success(request, "Primary image updated.")
    return redirect("inventory:product_detail", pk=pk)


# ---------- Barcodes ----------


@inventory_view_required
def product_barcode_image(request, pk):
    product = get_object_or_404(Product, pk=pk)
    png_bytes = generate_barcode_png(barcode_value_for(product))
    return HttpResponse(png_bytes, content_type="image/png")


@inventory_view_required
def product_barcode_print(request, pk):
    product = get_object_or_404(Product, pk=pk)
    try:
        quantity = max(1, min(int(request.GET.get("qty", "1")), 200))
    except ValueError:
        quantity = 1
    record_activity(
        user=request.user,
        action=InventoryActivityLog.Action.BARCODE_PRINTED,
        product=product,
        quantity_changed=quantity,
        remarks=f"Printed {quantity} label(s).",
        request=request,
    )
    return render(request, "inventory/barcode_print.html", {"labels": [product] * quantity})


@inventory_view_required
def barcode_bulk_select(request):
    products = Product.objects.filter(is_active=True).select_related("category", "brand")
    query = request.GET.get("q", "").strip()
    if query:
        products = products.filter(Q(name__icontains=query) | Q(sku__icontains=query))
    return render(request, "inventory/barcode_bulk_select.html", {"products": products, "query": query})


@inventory_view_required
def barcode_bulk_print(request):
    if request.method != "POST":
        return redirect("inventory:barcode_bulk_select")

    labels = []
    printed_counts = []  # (product, qty) — one activity log row per product, not per label copy
    for key, value in request.POST.items():
        if not key.startswith("qty_") or not value.strip():
            continue
        try:
            pk = int(key.replace("qty_", ""))
            qty = max(0, min(int(value), 200))
        except ValueError:
            continue
        if qty > 0:
            product = Product.objects.filter(pk=pk).first()
            if product:
                labels.extend([product] * qty)
                printed_counts.append((product, qty))

    if not labels:
        messages.error(request, "Select at least one product and quantity to print.")
        return redirect("inventory:barcode_bulk_select")

    for product, qty in printed_counts:
        record_activity(
            user=request.user,
            action=InventoryActivityLog.Action.BARCODE_PRINTED,
            product=product,
            quantity_changed=qty,
            remarks=f"Printed {qty} label(s) (bulk print).",
            request=request,
        )

    return render(request, "inventory/barcode_print.html", {"labels": labels})


# ---------- Inventory Activity Log (Administrator / Owner monitoring) ----------


@inventory_log_view_required
def activity_log_list(request):
    # effective_date: the business date an activity pertains to (e.g. the
    # date stock was actually received, possibly backdated) when set, else
    # the date the log row was created — so date/week/month filtering means
    # "what happened this month," not "what got typed into the system this
    # month."
    logs = InventoryActivityLog.objects.select_related("user", "product").annotate(
        effective_date=Coalesce("activity_date", TruncDate("created_at"))
    )

    quick = request.GET.get("quick", "").strip()
    date_from_raw = request.GET.get("date_from", "").strip()
    date_to_raw = request.GET.get("date_to", "").strip()
    month_raw = request.GET.get("month", "").strip()
    year_raw = request.GET.get("year", "").strip()
    user_id = request.GET.get("user", "").strip()
    action = request.GET.get("action", "").strip()
    query = request.GET.get("q", "").strip()

    date_from = date_to = None
    period_mode = "all"

    if quick and quick in {"today", "yesterday", "this_week", "last_week", "this_month", "last_month", "this_year"}:
        date_from, date_to = get_quick_range(quick)
        period_mode = quick
    elif month_raw and year_raw:
        try:
            date_from, date_to = month_range(int(year_raw), int(month_raw))
            period_mode = "month"
        except (ValueError, TypeError):
            pass
    elif date_from_raw or date_to_raw:
        date_from = parse_date(date_from_raw) if date_from_raw else None
        date_to = parse_date(date_to_raw) if date_to_raw else None
        period_mode = "custom"

    if date_from:
        logs = logs.filter(effective_date__gte=date_from)
    if date_to:
        logs = logs.filter(effective_date__lte=date_to)
    if user_id:
        logs = logs.filter(user_id=user_id)
    if action:
        logs = logs.filter(action=action)
    if query:
        logs = logs.filter(
            Q(product_name_snapshot__icontains=query)
            | Q(sku_snapshot__icontains=query)
            | Q(barcode_snapshot__icontains=query)
            | Q(product__part_number__icontains=query)
            | Q(product__oem_number__icontains=query)
        )

    logs = logs.order_by("-effective_date", "-created_at")

    stats = logs.aggregate(
        total_activities=Count("id"),
        products_added=Count("id", filter=Q(action=InventoryActivityLog.Action.PRODUCT_CREATED)),
        products_updated=Count(
            "id",
            filter=Q(action__in=[
                InventoryActivityLog.Action.PRODUCT_UPDATED,
                InventoryActivityLog.Action.PRODUCT_DEACTIVATED,
            ]),
        ),
        stock_received=Count(
            "id",
            filter=Q(action__in=[
                InventoryActivityLog.Action.STOCK_RECEIVED,
                InventoryActivityLog.Action.STOCK_ADDED,
            ]),
        ),
        stock_adjustments=Count("id", filter=Q(action=InventoryActivityLog.Action.STOCK_ADJUSTED)),
        shipments_received=Count("id", filter=Q(action=InventoryActivityLog.Action.SHIPMENT_RECEIVED)),
    )

    user_summary = (
        logs.filter(user__role=User.Roles.INVENTORY)
        .values("user_id", "user__first_name", "user__last_name", "user__username")
        .annotate(
            products_added=Count("id", filter=Q(action=InventoryActivityLog.Action.PRODUCT_CREATED)),
            stock_received=Count(
                "id",
                filter=Q(action__in=[
                    InventoryActivityLog.Action.STOCK_RECEIVED,
                    InventoryActivityLog.Action.STOCK_ADDED,
                ]),
            ),
            adjustments=Count("id", filter=Q(action=InventoryActivityLog.Action.STOCK_ADJUSTED)),
            total_activities=Count("id"),
        )
        .order_by("-total_activities")
    )

    paginator = Paginator(logs, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    all_effective_dates = InventoryActivityLog.objects.annotate(
        effective_date=Coalesce("activity_date", TruncDate("created_at"))
    ).values_list("effective_date", flat=True)
    years_with_logs = sorted(
        {d.year for d in all_effective_dates if d} | {date.today().year},
        reverse=True,
    )
    inventory_users = User.objects.filter(role=User.Roles.INVENTORY).order_by("first_name", "username")
    selected_user_obj = inventory_users.filter(pk=user_id).first() if user_id else None
    selected_action_label = dict(InventoryActivityLog.Action.choices).get(action, action)

    context = {
        "page_obj": page_obj,
        "stats": stats,
        "user_summary": user_summary,
        "inventory_users": inventory_users,
        "selected_user_obj": selected_user_obj,
        "selected_action_label": selected_action_label,
        "actions": InventoryActivityLog.Action.choices,
        "years": years_with_logs,
        "months": list(enumerate(calendar.month_name))[1:],
        "query": query,
        "selected_user": user_id,
        "selected_action": action,
        "selected_quick": quick,
        "selected_month": month_raw,
        "selected_year": year_raw,
        "date_from": date_from_raw,
        "date_to": date_to_raw,
        "period_mode": period_mode,
        "period_label": format_period_label(date_from, date_to),
        "results_count": stats["total_activities"],
    }
    return render(request, "inventory/activity_log_list.html", context)
