from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.sessions.models import Session
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    class Roles(models.TextChoices):
        ADMIN = "ADMIN", "Administrator"
        OWNER = "OWNER", "Owner"
        INVENTORY = "INVENTORY", "Inventory In-Charge"
        CASHIER = "CASHIER", "Cashier"
        ACCOUNTING = "ACCOUNTING", "Accounting In-Charge"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Roles.choices, default=Roles.CASHIER)
    profile_image = models.ImageField(upload_to="profile_images/", blank=True, null=True)
    # Session that currently owns this account; used to prevent simultaneous logins.
    active_session_key = models.CharField(max_length=40, blank=True, default="", editable=False)
    last_activity = models.DateTimeField(null=True, blank=True, editable=False)

    REQUIRED_FIELDS = ["email", "role"]

    class Meta:
        ordering = ["-date_joined"]

    def __str__(self):
        return self.get_full_name() or self.username

    def has_other_active_session(self, current_session_key=None):
        """True if this account is in use by a different, still-live session.

        A session counts as live while it exists, has not expired, and had activity
        within SINGLE_LOGIN_IDLE_MINUTES. This lets an account be reused after a
        browser was closed without logging out.
        """
        key = self.active_session_key
        if not key or key == current_session_key or not self.last_activity:
            return False
        idle_limit = timedelta(minutes=settings.SINGLE_LOGIN_IDLE_MINUTES)
        if timezone.now() - self.last_activity > idle_limit:
            return False
        return Session.objects.filter(session_key=key, expire_date__gt=timezone.now()).exists()

    @property
    def is_administrator(self):
        return self.role == self.Roles.ADMIN

    @property
    def is_owner(self):
        return self.role == self.Roles.OWNER

    @property
    def is_inventory_incharge(self):
        return self.role == self.Roles.INVENTORY

    @property
    def is_cashier(self):
        return self.role == self.Roles.CASHIER

    @property
    def is_accounting_incharge(self):
        return self.role == self.Roles.ACCOUNTING
