from django import forms
from django.conf import settings
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import User

INPUT_CLASS = "form-control"
SELECT_CLASS = "form-select"


class SingleLoginMixin:
    """Refuse a login while the account is in use by another live session."""

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        current_key = self.request.session.session_key if self.request else None
        if user.has_other_active_session(current_key):
            raise ValidationError(
                "This account is already logged in on another device. Log out there first, "
                "or try again after %(minutes)d minutes of inactivity.",
                code="already_logged_in",
                params={"minutes": settings.SINGLE_LOGIN_IDLE_MINUTES},
            )


class AdminLoginForm(SingleLoginMixin, AdminAuthenticationForm):
    pass


class LoginForm(SingleLoginMixin, AuthenticationForm):
    username = forms.CharField(
        label="Username or Email",
        widget=forms.TextInput(
            attrs={"class": INPUT_CLASS, "placeholder": "Enter username or email", "autofocus": True}
        ),
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"class": INPUT_CLASS, "placeholder": "Enter password"}),
    )
    error_messages = {
        "invalid_login": "Invalid username/email or password. Please try again.",
        "inactive": "This account has been deactivated. Please contact an administrator.",
    }


class UserCreateForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Password", widget=forms.PasswordInput(attrs={"class": INPUT_CLASS}), min_length=8
    )
    password2 = forms.CharField(
        label="Confirm Password", widget=forms.PasswordInput(attrs={"class": INPUT_CLASS}), min_length=8
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "email", "role"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": INPUT_CLASS}),
            "last_name": forms.TextInput(attrs={"class": INPUT_CLASS}),
            "username": forms.TextInput(attrs={"class": INPUT_CLASS}),
            "email": forms.EmailInput(attrs={"class": INPUT_CLASS}),
            "role": forms.Select(attrs={"class": SELECT_CLASS}),
        }

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("A user with this username already exists.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("A user with this email already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "Passwords do not match.")
        if password1:
            try:
                validate_password(password1)
            except ValidationError as exc:
                self.add_error("password1", exc)
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "email", "role", "is_active"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": INPUT_CLASS}),
            "last_name": forms.TextInput(attrs={"class": INPUT_CLASS}),
            "username": forms.TextInput(attrs={"class": INPUT_CLASS}),
            "email": forms.EmailInput(attrs={"class": INPUT_CLASS}),
            "role": forms.Select(attrs={"class": SELECT_CLASS}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exclude(pk=self.instance.pk).exists():
            raise ValidationError("A user with this username already exists.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError("A user with this email already exists.")
        return email


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "profile_image"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": INPUT_CLASS}),
            "last_name": forms.TextInput(attrs={"class": INPUT_CLASS}),
            "email": forms.EmailInput(attrs={"class": INPUT_CLASS}),
            "profile_image": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError("A user with this email already exists.")
        return email


class UserPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({"class": INPUT_CLASS})
