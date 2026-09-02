from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from .validators import normalize_identifier, normalize_name


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Category(TimeStampedModel):
    name = models.CharField(max_length=150)
    normalized_name = models.CharField(max_length=150, editable=False)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="subcategories"
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["normalized_name", "parent"], name="uniq_category_name_per_parent"
            ),
        ]
        verbose_name_plural = "Categories"

    def __str__(self):
        return f"{self.parent.name} / {self.name}" if self.parent else self.name

    def clean(self):
        self.normalized_name = normalize_name(self.name)
        if not self.normalized_name:
            raise ValidationError({"name": "Category name is required."})
        # MySQL does not treat NULL as equal in unique indexes, so top-level
        # (parent=None) duplicates must be checked explicitly at the app layer.
        conflict = Category.objects.filter(
            normalized_name=self.normalized_name, parent=self.parent
        ).exclude(pk=self.pk)
        if conflict.exists():
            raise ValidationError({"name": "A category with this name already exists at this level."})


class Brand(TimeStampedModel):
    name = models.CharField(max_length=150)
    normalized_name = models.CharField(max_length=150, unique=True, editable=False)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def clean(self):
        self.normalized_name = normalize_name(self.name)
        if not self.normalized_name:
            raise ValidationError({"name": "Brand name is required."})
        # normalized_name isn't a form field, so Django's automatic
        # validate_unique() excludes it from checking (see Category.clean()
        # for the same reasoning) — the duplicate check has to happen here.
        if Brand.objects.filter(normalized_name=self.normalized_name).exclude(pk=self.pk).exists():
            raise ValidationError({"name": "A brand with this name already exists."})


class Manufacturer(TimeStampedModel):
    name = models.CharField(max_length=150)
    normalized_name = models.CharField(max_length=150, unique=True, editable=False)
    country = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def clean(self):
        self.normalized_name = normalize_name(self.name)
        if not self.normalized_name:
            raise ValidationError({"name": "Manufacturer name is required."})
        if Manufacturer.objects.filter(normalized_name=self.normalized_name).exclude(pk=self.pk).exists():
            raise ValidationError({"name": "A manufacturer with this name already exists."})


class Supplier(TimeStampedModel):
    name = models.CharField(max_length=150)
    normalized_name = models.CharField(max_length=150, unique=True, editable=False)
    contact_person = models.CharField(max_length=150, blank=True)
    contact_number = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    tax_information = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def clean(self):
        self.normalized_name = normalize_name(self.name)
        if not self.normalized_name:
            raise ValidationError({"name": "Supplier name is required."})
        if Supplier.objects.filter(normalized_name=self.normalized_name).exclude(pk=self.pk).exists():
            raise ValidationError({"name": "A supplier with this name already exists."})


class ProductAttribute(TimeStampedModel):
    class DataType(models.TextChoices):
        TEXT = "TEXT", "Text"
        NUMBER = "NUMBER", "Number"

    name = models.CharField(max_length=100)
    normalized_name = models.CharField(max_length=100, unique=True, editable=False)
    data_type = models.CharField(max_length=10, choices=DataType.choices, default=DataType.TEXT)
    unit = models.CharField(max_length=20, blank=True, help_text="e.g. mm, V, L")
    applicable_categories = models.ManyToManyField(
        Category, blank=True, related_name="attributes",
        help_text="Leave empty to make this attribute available for every category.",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def clean(self):
        self.normalized_name = normalize_name(self.name)
        if not self.normalized_name:
            raise ValidationError({"name": "Attribute name is required."})
        if ProductAttribute.objects.filter(normalized_name=self.normalized_name).exclude(pk=self.pk).exists():
            raise ValidationError({"name": "An attribute with this name already exists."})


class Product(TimeStampedModel):
    class UnitOfMeasurement(models.TextChoices):
        PIECE = "PCS", "Piece"
        SET = "SET", "Set"
        BOX = "BOX", "Box"
        PAIR = "PAIR", "Pair"
        ROLL = "ROLL", "Roll"
        KILOGRAM = "KG", "Kilogram"
        GRAM = "G", "Gram"
        LITER = "L", "Liter"
        MILLILITER = "ML", "Milliliter"
        METER = "M", "Meter"
        CENTIMETER = "CM", "Centimeter"
        MILLIMETER = "MM", "Millimeter"

    # --- Identifiers ---
    sku = models.CharField(max_length=64, unique=True)
    barcode_number = models.CharField(max_length=64, unique=True, null=True, blank=True)
    name = models.CharField(max_length=200)
    normalized_name = models.CharField(max_length=200, editable=False)
    short_description = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)

    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    brand = models.ForeignKey(
        Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name="products"
    )
    manufacturer = models.ForeignKey(
        Manufacturer, on_delete=models.SET_NULL, null=True, blank=True, related_name="products"
    )
    made_by = models.CharField(max_length=150, blank=True)
    country_of_origin = models.CharField(max_length=100, blank=True)

    model_number = models.CharField(max_length=100, blank=True)
    part_number = models.CharField(max_length=100, null=True, blank=True)
    oem_number = models.CharField(max_length=100, null=True, blank=True)
    alternate_part_number = models.CharField(max_length=100, blank=True)
    supplier_part_number = models.CharField(max_length=100, blank=True)

    # --- Physical attributes ---
    color = models.CharField(max_length=50, blank=True)
    material = models.CharField(max_length=100, blank=True)
    finish = models.CharField(max_length=100, blank=True)
    size = models.CharField(max_length=50, blank=True)
    length = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, validators=[MinValueValidator(0)])
    width = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, validators=[MinValueValidator(0)])
    height = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, validators=[MinValueValidator(0)])
    diameter = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, validators=[MinValueValidator(0)])
    thickness = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, validators=[MinValueValidator(0)])
    weight = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, validators=[MinValueValidator(0)])
    unit_of_measurement = models.CharField(
        max_length=10, choices=UnitOfMeasurement.choices, default=UnitOfMeasurement.PIECE
    )
    packaging_type = models.CharField(max_length=100, blank=True)
    quantity_per_package = models.PositiveIntegerField(null=True, blank=True)

    # --- Pricing (Decimal only — never float) ---
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    wholesale_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    retail_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    suggested_retail_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    selling_price = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    discounted_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    minimum_selling_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])

    # --- Stock control (full batch/FIFO tracking is Milestone 2; this is a
    # single running total, only ever changed through services.add_stock()
    # so every change gets a dated, logged InventoryActivityLog row) ---
    quantity_on_hand = models.PositiveIntegerField(default=0)
    reorder_level = models.PositiveIntegerField(default=0)

    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            # NULL is treated as distinct per-row by MySQL's unique index, so this
            # only enforces uniqueness when both values are actually provided —
            # exactly the "unique when provided, scoped to manufacturer/brand"
            # behavior the spec asks for, without relying on partial/conditional
            # indexes (which MySQL does not support).
            models.UniqueConstraint(fields=["manufacturer", "oem_number"], name="uniq_manufacturer_oem_number"),
            models.UniqueConstraint(fields=["brand", "part_number"], name="uniq_brand_part_number"),
        ]
        indexes = [
            models.Index(fields=["normalized_name"]),
            models.Index(fields=["category"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.sku})"

    def clean(self):
        self.normalized_name = normalize_name(self.name)
        if not self.normalized_name:
            raise ValidationError({"name": "Product name is required."})

        self.sku = (self.sku or "").strip().upper()
        self.barcode_number = normalize_identifier(self.barcode_number)
        self.part_number = normalize_identifier(self.part_number)
        self.oem_number = normalize_identifier(self.oem_number)

        if (
            self.minimum_selling_price is not None
            and self.selling_price is not None
            and self.minimum_selling_price > self.selling_price
        ):
            raise ValidationError(
                {"minimum_selling_price": "Minimum selling price cannot exceed the selling price."}
            )

    @property
    def primary_image(self):
        return self.images.filter(is_primary=True).first() or self.images.first()


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="products/%Y/%m/")
    is_primary = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "created_at"]

    def __str__(self):
        return f"Image for {self.product.name}"


class ProductCompatibility(models.Model):
    class VehicleType(models.TextChoices):
        CAR = "CAR", "Car"
        MOTORCYCLE = "MOTORCYCLE", "Motorcycle"
        TRUCK = "TRUCK", "Truck"
        SUV = "SUV", "SUV"
        VAN = "VAN", "Van"
        BUS = "BUS", "Bus"
        OTHER = "OTHER", "Other"

    class FuelType(models.TextChoices):
        PETROL = "PETROL", "Petrol"
        DIESEL = "DIESEL", "Diesel"
        ELECTRIC = "ELECTRIC", "Electric"
        HYBRID = "HYBRID", "Hybrid"
        LPG = "LPG", "LPG"
        OTHER = "OTHER", "Other"

    class TransmissionType(models.TextChoices):
        MANUAL = "MANUAL", "Manual"
        AUTOMATIC = "AUTOMATIC", "Automatic"
        CVT = "CVT", "CVT"
        OTHER = "OTHER", "Other"

    class DriveType(models.TextChoices):
        FWD = "FWD", "FWD"
        RWD = "RWD", "RWD"
        AWD = "AWD", "AWD"
        FOUR_WD = "4WD", "4WD"

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="compatibilities")
    vehicle_type = models.CharField(max_length=15, choices=VehicleType.choices, default=VehicleType.CAR)
    vehicle_brand = models.CharField(max_length=100, blank=True)
    vehicle_manufacturer = models.CharField(max_length=100, blank=True)
    vehicle_model = models.CharField(max_length=100, blank=True)
    vehicle_variant = models.CharField(max_length=100, blank=True)
    vehicle_generation = models.CharField(max_length=100, blank=True)
    year_from = models.PositiveIntegerField(null=True, blank=True)
    year_to = models.PositiveIntegerField(null=True, blank=True)
    engine_type = models.CharField(max_length=100, blank=True)
    engine_code = models.CharField(max_length=100, blank=True)
    engine_displacement = models.CharField(max_length=50, blank=True)
    fuel_type = models.CharField(max_length=10, choices=FuelType.choices, blank=True)
    transmission_type = models.CharField(max_length=10, choices=TransmissionType.choices, blank=True)
    drive_type = models.CharField(max_length=5, choices=DriveType.choices, blank=True)

    class Meta:
        ordering = ["vehicle_brand", "vehicle_model"]
        verbose_name_plural = "Product compatibilities"

    def __str__(self):
        return f"{self.vehicle_brand} {self.vehicle_model}".strip() or "Compatibility entry"

    def clean(self):
        if self.year_from and self.year_to and self.year_from > self.year_to:
            raise ValidationError({"year_to": "Year To cannot be earlier than Year From."})


class ProductAttributeValue(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="attribute_values")
    attribute = models.ForeignKey(ProductAttribute, on_delete=models.PROTECT, related_name="values")
    value = models.CharField(max_length=255)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["product", "attribute"], name="uniq_product_attribute"),
        ]

    def __str__(self):
        return f"{self.attribute.name}: {self.value}"


class ProductSupplier(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="supplier_links")
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name="product_links")
    supplier_sku = models.CharField(max_length=100, blank=True)
    supplier_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)]
    )
    is_preferred = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["product", "supplier"], name="uniq_product_supplier"),
        ]

    def __str__(self):
        return f"{self.product.name} — {self.supplier.name}"


class ProductPriceHistory(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="price_history")
    field_name = models.CharField(max_length=50)
    old_price = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    new_price = models.DecimalField(max_digits=12, decimal_places=2)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-changed_at"]
        verbose_name_plural = "Product price histories"

    def __str__(self):
        return f"{self.product.sku}: {self.field_name} {self.old_price} -> {self.new_price}"


class InventoryActivityLog(models.Model):
    """Immutable audit trail of inventory activity. Rows are only ever
    created (via services.record_activity / record_product_field_changes),
    never updated or deleted — see apps/inventory/admin.py, which locks the
    Django admin down to read-only for this model, and apps/inventory/views.py,
    which exposes no edit/delete endpoints for it.

    Shipment/Batch/FIFO action types are defined now so no migration is
    needed when that module (Milestone 2) is built, but they are not fired
    by any code path yet since those models do not exist.
    """

    class Action(models.TextChoices):
        PRODUCT_CREATED = "PRODUCT_CREATED", "Product Created"
        PRODUCT_UPDATED = "PRODUCT_UPDATED", "Product Updated"
        PRODUCT_DEACTIVATED = "PRODUCT_DEACTIVATED", "Product Deactivated"
        STOCK_RECEIVED = "STOCK_RECEIVED", "Stock Received"
        STOCK_ADDED = "STOCK_ADDED", "Stock Added"
        STOCK_DEDUCTED = "STOCK_DEDUCTED", "Stock Deducted"
        STOCK_ADJUSTED = "STOCK_ADJUSTED", "Stock Adjusted"
        SHIPMENT_CREATED = "SHIPMENT_CREATED", "Shipment Created"
        SHIPMENT_RECEIVED = "SHIPMENT_RECEIVED", "Shipment Received"
        BATCH_CREATED = "BATCH_CREATED", "Batch Created"
        STOCK_RETURNED = "STOCK_RETURNED", "Stock Returned"
        STOCK_DAMAGED = "STOCK_DAMAGED", "Stock Damaged"
        STOCK_EXPIRED = "STOCK_EXPIRED", "Stock Expired"
        BARCODE_GENERATED = "BARCODE_GENERATED", "Barcode Generated"
        BARCODE_PRINTED = "BARCODE_PRINTED", "Barcode Printed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="inventory_activity_logs"
    )
    action = models.CharField(max_length=30, choices=Action.choices)

    product = models.ForeignKey(
        Product, on_delete=models.SET_NULL, null=True, blank=True, related_name="activity_logs"
    )
    # Snapshotted so the log still reads correctly even if the product is
    # later renamed, re-SKU'd, or deleted.
    product_name_snapshot = models.CharField(max_length=200, blank=True)
    sku_snapshot = models.CharField(max_length=64, blank=True)
    barcode_snapshot = models.CharField(max_length=64, blank=True)

    quantity_before = models.IntegerField(null=True, blank=True)
    quantity_changed = models.IntegerField(null=True, blank=True)
    quantity_after = models.IntegerField(null=True, blank=True)

    # The business date the activity pertains to (e.g. the date stock was
    # actually received, which may be entered a day or two after the fact) —
    # distinct from created_at below, which is the immutable system
    # timestamp of when this audit row was written. Left null for actions
    # with no meaningful business date (product create/update, barcode
    # printing); the log list view falls back to created_at's date for those.
    activity_date = models.DateField(null=True, blank=True)

    # Loose text linkage rather than hard FKs, since Batch/Shipment models
    # don't exist yet — see the class docstring.
    reference_type = models.CharField(max_length=30, blank=True)
    reference_id = models.CharField(max_length=100, blank=True)

    field_name = models.CharField(max_length=50, blank=True)
    previous_value = models.CharField(max_length=255, blank=True)
    new_value = models.CharField(max_length=255, blank=True)

    remarks = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["action"]),
            models.Index(fields=["user"]),
            models.Index(fields=["product"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["activity_date"]),
        ]

    def __str__(self):
        label = self.product_name_snapshot or self.sku_snapshot or "—"
        return f"{self.get_action_display()} — {label} @ {self.created_at:%Y-%m-%d %H:%M}"
