from django.contrib.auth.decorators import login_required
from django.db.models import Count, F, Q, Sum
from django.shortcuts import render

from apps.accounts.models import User
from apps.inventory.models import Brand, Category, InventoryActivityLog, Manufacturer, Product

ROLE_TEMPLATES = {
    User.Roles.ADMIN: "dashboard/admin_dashboard.html",
    User.Roles.OWNER: "dashboard/owner_dashboard.html",
    User.Roles.INVENTORY: "dashboard/inventory_dashboard.html",
    User.Roles.CASHIER: "dashboard/cashier_dashboard.html",
    User.Roles.ACCOUNTING: "dashboard/accounting_dashboard.html",
}


@login_required
def dashboard_view(request):
    role = request.user.role
    context = {}

    if request.user.is_superuser or role == User.Roles.ADMIN:
        context.update(
            {
                "total_users": User.objects.count(),
                "active_users": User.objects.filter(is_active=True).count(),
                "inactive_users": User.objects.filter(is_active=False).count(),
                "total_admins": User.objects.filter(role=User.Roles.ADMIN).count(),
                "total_owners": User.objects.filter(role=User.Roles.OWNER).count(),
                "total_inventory": User.objects.filter(role=User.Roles.INVENTORY).count(),
                "total_cashiers": User.objects.filter(role=User.Roles.CASHIER).count(),
                "total_accounting": User.objects.filter(role=User.Roles.ACCOUNTING).count(),
            }
        )
        template = "dashboard/admin_dashboard.html"
    else:
        template = ROLE_TEMPLATES.get(role, "dashboard/cashier_dashboard.html")

    if role == User.Roles.OWNER:
        context["recent_inventory_activity"] = (
            InventoryActivityLog.objects.select_related("user", "product").all()[:10]
        )

    if role == User.Roles.INVENTORY:
        active_products = Product.objects.filter(is_active=True)
        context.update(
            {
                "total_products": active_products.count(),
                "total_categories": Category.objects.filter(is_active=True).count(),
                "total_brands": Brand.objects.filter(is_active=True).count(),
                "total_manufacturers": Manufacturer.objects.filter(is_active=True).count(),
                "total_stock_on_hand": active_products.aggregate(total=Sum("quantity_on_hand"))["total"] or 0,
                "low_stock_count": active_products.filter(quantity_on_hand__lte=F("reorder_level")).count(),
                "recent_products": Product.objects.filter(is_active=True)
                .select_related("category", "brand", "manufacturer")
                .order_by("-created_at")[:8],
                "products_by_category": Category.objects.filter(is_active=True)
                .annotate(product_count=Count("products", filter=Q(products__is_active=True)))
                .order_by("-product_count", "name")[:10],
                "products_by_brand": Brand.objects.filter(is_active=True)
                .annotate(product_count=Count("products", filter=Q(products__is_active=True)))
                .order_by("-product_count", "name")[:10],
                "products_by_manufacturer": Manufacturer.objects.filter(is_active=True)
                .annotate(product_count=Count("products", filter=Q(products__is_active=True)))
                .order_by("-product_count", "name")[:10],
            }
        )

    return render(request, template, context)
