from django.urls import path

from . import views

app_name = "inventory"

urlpatterns = [
    path("", views.product_list, name="index"),
    # Products
    path("products/", views.product_list, name="product_list"),
    path("products/create/", views.product_create, name="product_create"),
    path("products/<int:pk>/", views.product_detail, name="product_detail"),
    path("products/<int:pk>/edit/", views.product_edit, name="product_edit"),
    path("products/<int:pk>/images/upload/", views.product_image_upload, name="product_image_upload"),
    path("products/<int:pk>/images/<int:image_id>/delete/", views.product_image_delete, name="product_image_delete"),
    path(
        "products/<int:pk>/images/<int:image_id>/set-primary/",
        views.product_image_set_primary,
        name="product_image_set_primary",
    ),
    # Barcodes
    path("products/<int:pk>/barcode/", views.product_barcode_image, name="product_barcode_image"),
    path("products/<int:pk>/barcode/print/", views.product_barcode_print, name="product_barcode_print"),
    path("barcodes/print/", views.barcode_bulk_select, name="barcode_bulk_select"),
    path("barcodes/print/run/", views.barcode_bulk_print, name="barcode_bulk_print"),
    # Categories
    path("categories/", views.category_list, name="category_list"),
    path("categories/<int:pk>/edit/", views.category_edit, name="category_edit"),
    path("categories/<int:pk>/toggle-status/", views.category_toggle, name="category_toggle"),
    # Brands
    path("brands/", views.brand_list, name="brand_list"),
    path("brands/<int:pk>/edit/", views.brand_edit, name="brand_edit"),
    path("brands/<int:pk>/toggle-status/", views.brand_toggle, name="brand_toggle"),
    # Manufacturers
    path("manufacturers/", views.manufacturer_list, name="manufacturer_list"),
    path("manufacturers/<int:pk>/edit/", views.manufacturer_edit, name="manufacturer_edit"),
    path("manufacturers/<int:pk>/toggle-status/", views.manufacturer_toggle, name="manufacturer_toggle"),
    # Suppliers
    path("suppliers/", views.supplier_list, name="supplier_list"),
    path("suppliers/<int:pk>/edit/", views.supplier_edit, name="supplier_edit"),
    path("suppliers/<int:pk>/toggle-status/", views.supplier_toggle, name="supplier_toggle"),
]
