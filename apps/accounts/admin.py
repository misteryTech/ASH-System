from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .forms import AdminLoginForm
from .models import User

admin.site.login_form = AdminLoginForm


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ["username", "email", "first_name", "last_name", "role", "is_active", "is_staff"]
    list_filter = ["role", "is_active", "is_staff"]
    fieldsets = UserAdmin.fieldsets + (
        ("Role & Profile", {"fields": ("role", "profile_image")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Role & Profile", {"fields": ("email", "role", "profile_image")}),
    )
