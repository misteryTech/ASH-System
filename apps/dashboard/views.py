from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.accounts.models import User

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

    return render(request, template, context)
