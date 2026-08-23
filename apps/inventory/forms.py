from django import forms
from django.forms import inlineformset_factory

from .models import (
    Brand,
    Category,
    Manufacturer,
    Product,
    ProductAttributeValue,
    ProductCompatibility,
    ProductImage,
    Supplier,
)
from .services import generate_sku
from .validators import validate_image_file

INPUT_CLASS = "form-control"
SELECT_CLASS = "form-select"


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "parent", "description", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": INPUT_CLASS}),
            "parent": forms.Select(attrs={"class": SELECT_CLASS}),
            "description": forms.Textarea(attrs={"class": INPUT_CLASS, "rows": 2}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["parent"].queryset = Category.objects.filter(parent__isnull=True)
        self.fields["parent"].required = False


class BrandForm(forms.ModelForm):
    class Meta:
        model = Brand
        fields = ["name", "description", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": INPUT_CLASS}),
            "description": forms.Textarea(attrs={"class": INPUT_CLASS, "rows": 2}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class ManufacturerForm(forms.ModelForm):
    class Meta:
        model = Manufacturer
        fields = ["name", "country", "description", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": INPUT_CLASS}),
            "country": forms.TextInput(attrs={"class": INPUT_CLASS}),
            "description": forms.Textarea(attrs={"class": INPUT_CLASS, "rows": 2}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = [
            "name", "contact_person", "contact_number", "email", "address",
            "tax_information", "is_active",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": INPUT_CLASS}),
            "contact_person": forms.TextInput(attrs={"class": INPUT_CLASS}),
            "contact_number": forms.TextInput(attrs={"class": INPUT_CLASS}),
            "email": forms.EmailInput(attrs={"class": INPUT_CLASS}),
            "address": forms.Textarea(attrs={"class": INPUT_CLASS, "rows": 2}),
            "tax_information": forms.TextInput(attrs={"class": INPUT_CLASS}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


PRODUCT_FIELDS = [
    "sku", "barcode_number", "name", "short_description", "description",
    "category", "brand", "manufacturer", "made_by", "country_of_origin",
    "model_number", "part_number", "oem_number", "alternate_part_number",
    "supplier_part_number",
    "color", "material", "finish", "size", "length", "width", "height",
    "diameter", "thickness", "weight", "unit_of_measurement",
    "packaging_type", "quantity_per_package",
    "cost_price", "wholesale_price", "retail_price", "suggested_retail_price",
    "selling_price", "discounted_price", "minimum_selling_price",
    "reorder_level", "is_active",
]

_TEXT_FIELDS = [
    "name", "short_description", "made_by", "country_of_origin", "model_number",
    "part_number", "oem_number", "alternate_part_number", "supplier_part_number",
    "color", "material", "finish", "size", "packaging_type",
]
_NUMBER_FIELDS = [
    "length", "width", "height", "diameter", "thickness", "weight",
    "quantity_per_package", "cost_price", "wholesale_price", "retail_price",
    "suggested_retail_price", "selling_price", "discounted_price",
    "minimum_selling_price", "reorder_level",
]


class ProductForm(forms.ModelForm):
    sku = forms.CharField(
        required=False,
        label="SKU",
        help_text="Leave blank to auto-generate from category and brand.",
        widget=forms.TextInput(attrs={"class": INPUT_CLASS}),
    )
    barcode_number = forms.CharField(
        required=False,
        label="Barcode Number",
        help_text="Leave blank to use the SKU as the barcode value.",
        widget=forms.TextInput(attrs={"class": INPUT_CLASS}),
    )
    confirm_duplicate = forms.BooleanField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = Product
        fields = PRODUCT_FIELDS
        widgets = {
            "description": forms.Textarea(attrs={"class": INPUT_CLASS, "rows": 3}),
            "category": forms.Select(attrs={"class": SELECT_CLASS}),
            "brand": forms.Select(attrs={"class": SELECT_CLASS}),
            "manufacturer": forms.Select(attrs={"class": SELECT_CLASS}),
            "unit_of_measurement": forms.Select(attrs={"class": SELECT_CLASS}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in _TEXT_FIELDS:
            self.fields[field_name].widget.attrs.setdefault("class", INPUT_CLASS)
        for field_name in _NUMBER_FIELDS:
            self.fields[field_name].widget.attrs.setdefault("class", INPUT_CLASS)
        self.fields["category"].queryset = Category.objects.filter(is_active=True)
        self.fields["brand"].queryset = Brand.objects.filter(is_active=True)
        self.fields["manufacturer"].queryset = Manufacturer.objects.filter(is_active=True)

    def clean(self):
        cleaned_data = super().clean()
        min_price = cleaned_data.get("minimum_selling_price")
        selling_price = cleaned_data.get("selling_price")
        if min_price is not None and selling_price is not None and min_price > selling_price:
            self.add_error("minimum_selling_price", "Minimum selling price cannot exceed the selling price.")

        # Generated here (not in the view) so the SKU is already non-blank by
        # the time ModelForm._post_clean() runs instance.full_clean() — doing
        # it after is_valid() would be too late and fail the model's blank check.
        if not cleaned_data.get("sku") and cleaned_data.get("category"):
            cleaned_data["sku"] = generate_sku(cleaned_data["category"], cleaned_data.get("brand"))

        return cleaned_data


class ProductImageForm(forms.Form):
    image = forms.ImageField(widget=forms.ClearableFileInput(attrs={"class": "form-control"}))
    is_primary = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={"class": "form-check-input"}))

    def clean_image(self):
        image = self.cleaned_data["image"]
        validate_image_file(image)
        return image


ProductCompatibilityFormSet = inlineformset_factory(
    Product,
    ProductCompatibility,
    fields=[
        "vehicle_type", "vehicle_brand", "vehicle_manufacturer", "vehicle_model",
        "vehicle_variant", "vehicle_generation", "year_from", "year_to",
        "engine_type", "engine_code", "engine_displacement", "fuel_type",
        "transmission_type", "drive_type",
    ],
    widgets={
        "vehicle_type": forms.Select(attrs={"class": SELECT_CLASS}),
        "vehicle_brand": forms.TextInput(attrs={"class": INPUT_CLASS}),
        "vehicle_manufacturer": forms.TextInput(attrs={"class": INPUT_CLASS}),
        "vehicle_model": forms.TextInput(attrs={"class": INPUT_CLASS}),
        "vehicle_variant": forms.TextInput(attrs={"class": INPUT_CLASS}),
        "vehicle_generation": forms.TextInput(attrs={"class": INPUT_CLASS}),
        "year_from": forms.NumberInput(attrs={"class": INPUT_CLASS}),
        "year_to": forms.NumberInput(attrs={"class": INPUT_CLASS}),
        "engine_type": forms.TextInput(attrs={"class": INPUT_CLASS}),
        "engine_code": forms.TextInput(attrs={"class": INPUT_CLASS}),
        "engine_displacement": forms.TextInput(attrs={"class": INPUT_CLASS}),
        "fuel_type": forms.Select(attrs={"class": SELECT_CLASS}),
        "transmission_type": forms.Select(attrs={"class": SELECT_CLASS}),
        "drive_type": forms.Select(attrs={"class": SELECT_CLASS}),
    },
    extra=2,
    can_delete=True,
)

ProductAttributeValueFormSet = inlineformset_factory(
    Product,
    ProductAttributeValue,
    fields=["attribute", "value"],
    widgets={
        "attribute": forms.Select(attrs={"class": SELECT_CLASS}),
        "value": forms.TextInput(attrs={"class": INPUT_CLASS}),
    },
    extra=6,
    can_delete=True,
)
