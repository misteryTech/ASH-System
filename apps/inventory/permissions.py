from apps.accounts.decorators import role_required
from apps.accounts.models import User

inventory_manage_required = role_required(User.Roles.ADMIN, User.Roles.INVENTORY)
inventory_view_required = role_required(
    User.Roles.ADMIN, User.Roles.OWNER, User.Roles.INVENTORY, User.Roles.ACCOUNTING
)

# Activity log page: Administrator has full access, Owner is read-only
# monitoring per spec section 28. Inventory In-Charge and Accounting are not
# given a dedicated log page (spec calls it "Administrator-only" in section
# 13); Cashier has no access at all.
inventory_log_view_required = role_required(User.Roles.ADMIN, User.Roles.OWNER)
