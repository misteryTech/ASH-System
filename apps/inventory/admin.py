from django.contrib import admin

from .models import (
    Brand,
    Category,
    Manufacturer,
    Product,
    ProductAttribute,
    ProductAttributeValue,
    ProductCompatibility,
    ProductImage,
    ProductPriceHistory,
    ProductSupplier,
    Supplier,
)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class ProductCompatibilityInline(admin.TabularInline):
    model = ProductCompatibility
    extra = 0


class ProductAttributeValueInline(admin.TabularInline):
    model = ProductAttributeValue
    extra = 0


class ProductSupplierInline(admin.TabularInline):
    model = ProductSupplier
    extra = 0


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["sku", "name", "category", "brand", "selling_price", "is_active"]
    list_filter = ["category", "brand", "is_active"]
    search_fields = ["sku", "name", "barcode_number", "part_number", "oem_number"]
    inlines = [ProductImageInline, ProductCompatibilityInline, ProductAttributeValueInline, ProductSupplierInline]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "parent", "is_active"]
    search_fields = ["name"]


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ["name", "is_active"]
    search_fields = ["name"]


@admin.register(Manufacturer)
class ManufacturerAdmin(admin.ModelAdmin):
    list_display = ["name", "country", "is_active"]
    search_fields = ["name"]


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ["name", "contact_person", "contact_number", "is_active"]
    search_fields = ["name"]


@admin.register(ProductAttribute)
class ProductAttributeAdmin(admin.ModelAdmin):
    list_display = ["name", "data_type", "unit", "is_active"]
    search_fields = ["name"]


@admin.register(ProductPriceHistory)
class ProductPriceHistoryAdmin(admin.ModelAdmin):
    list_display = ["product", "field_name", "old_price", "new_price", "changed_by", "changed_at"]
    list_filter = ["field_name"]
