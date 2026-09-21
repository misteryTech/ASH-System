from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .decorators import admin_required
from .forms import LoginForm, ProfileForm, UserCreateForm, UserEditForm, UserPasswordChangeForm
from .models import User


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard:index")

    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            if not request.POST.get("remember_me"):
                request.session.set_expiry(0)
            messages.success(request, f"Welcome back, {user.get_full_name() or user.username}!")
            next_url = request.POST.get("next") or request.GET.get("next")
            return redirect(next_url or "dashboard:index")
        errors = form.non_field_errors()
        messages.error(request, errors[0] if errors else "Invalid username/email or password.")
    else:
        form = LoginForm(request)

    return render(request, "accounts/login.html", {"form": form})


def logout_view(request):
    if request.user.is_authenticated:
        logout(request)
        messages.success(request, "You have been logged out successfully.")
    return redirect("accounts:login")


@login_required
def profile_view(request):
    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("accounts:profile")
        messages.error(request, "Please correct the errors below.")
    else:
        form = ProfileForm(instance=request.user)

    return render(request, "accounts/profile.html", {"form": form})


@login_required
def change_password_view(request):
    if request.method == "POST":
        form = UserPasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            # The session key is rotated on password change; keep it as the active one.
            User.objects.filter(pk=user.pk).update(active_session_key=request.session.session_key)
            messages.success(request, "Password changed successfully.")
            return redirect("accounts:profile")
        messages.error(request, "Please correct the errors below.")
    else:
        form = UserPasswordChangeForm(user=request.user)

    return render(request, "accounts/change_password.html", {"form": form})


@admin_required
def register_redirect(request):
    return redirect("accounts:user_create")


def _is_last_active_admin(user_obj):
    if user_obj.role != User.Roles.ADMIN or not user_obj.is_active:
        return False
    return not User.objects.filter(role=User.Roles.ADMIN, is_active=True).exclude(pk=user_obj.pk).exists()


@admin_required
def user_list_view(request):
    query = request.GET.get("q", "").strip()
    role_filter = request.GET.get("role", "").strip()
    status_filter = request.GET.get("status", "").strip()

    users = User.objects.all()
    if query:
        users = users.filter(
            Q(username__icontains=query)
            | Q(email__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
        )
    if role_filter:
        users = users.filter(role=role_filter)
    if status_filter == "active":
        users = users.filter(is_active=True)
    elif status_filter == "inactive":
        users = users.filter(is_active=False)

    context = {
        "users": users,
        "query": query,
        "role_filter": role_filter,
        "status_filter": status_filter,
        "roles": User.Roles.choices,
    }
    return render(request, "users/user_list.html", context)


@admin_required
def user_create_view(request):
    if request.method == "POST":
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"User '{user.username}' created successfully.")
            return redirect("accounts:user_list")
        messages.error(request, "Please correct the errors below.")
    else:
        form = UserCreateForm()

    return render(request, "users/user_create.html", {"form": form})


@admin_required
def user_detail_view(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    return render(request, "users/user_detail.html", {"user_obj": user_obj})


@admin_required
def user_edit_view(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    was_last_admin = _is_last_active_admin(user_obj)

    if request.method == "POST":
        form = UserEditForm(request.POST, instance=user_obj)
        if form.is_valid():
            new_role = form.cleaned_data["role"]
            new_active = form.cleaned_data["is_active"]
            if was_last_admin and (new_role != User.Roles.ADMIN or not new_active):
                messages.error(
                    request, "Cannot change the role or deactivate the last active Administrator."
                )
            else:
                form.save()
                messages.success(request, f"User '{user_obj.username}' updated successfully.")
                return redirect("accounts:user_detail", pk=user_obj.pk)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = UserEditForm(instance=user_obj)

    return render(request, "users/user_edit.html", {"form": form, "user_obj": user_obj})


@admin_required
def user_toggle_status_view(request, pk):
    user_obj = get_object_or_404(User, pk=pk)

    if request.method != "POST":
        return redirect("accounts:user_detail", pk=pk)

    if user_obj.is_active and _is_last_active_admin(user_obj):
        messages.error(request, "Cannot deactivate the last active Administrator.")
        return redirect("accounts:user_detail", pk=pk)

    user_obj.is_active = not user_obj.is_active
    user_obj.save(update_fields=["is_active"])
    status = "activated" if user_obj.is_active else "deactivated"
    messages.success(request, f"User '{user_obj.username}' has been {status} successfully.")
    return redirect("accounts:user_detail", pk=pk)
