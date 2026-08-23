from apps.accounts.decorators import role_required
from apps.accounts.models import User

inventory_manage_required = role_required(User.Roles.ADMIN, User.Roles.INVENTORY)
inventory_view_required = role_required(
    User.Roles.ADMIN, User.Roles.OWNER, User.Roles.INVENTORY, User.Roles.ACCOUNTING
)
