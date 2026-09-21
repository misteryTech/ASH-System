from django.contrib.auth.models import AbstractUser
from django.db import models


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

    REQUIRED_FIELDS = ["email", "role"]

    class Meta:
        ordering = ["-date_joined"]

    def __str__(self):
        return self.get_full_name() or self.username

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
