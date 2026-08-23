from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register_redirect, name="register"),
    path("profile/", views.profile_view, name="profile"),
    path("change-password/", views.change_password_view, name="change_password"),
    path("users/", views.user_list_view, name="user_list"),
    path("users/create/", views.user_create_view, name="user_create"),
    path("users/<int:pk>/", views.user_detail_view, name="user_detail"),
    path("users/<int:pk>/edit/", views.user_edit_view, name="user_edit"),
    path("users/<int:pk>/toggle-status/", views.user_toggle_status_view, name="user_toggle_status"),
]
