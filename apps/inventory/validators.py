import os
import re

from django.core.exceptions import ValidationError

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


def normalize_name(value):
    if not value:
        return ""
    return re.sub(r"\s+", " ", value.strip()).lower()


def normalize_identifier(value):
    """Strip an optional identifier (SKU, barcode, part number) and turn a
    blank result into None so unique constraints only apply when provided."""
    if value is None:
        return None
    value = value.strip()
    return value or None


def validate_image_file(file):
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(
            f"Unsupported image type '{ext}'. Allowed types: "
            f"{', '.join(sorted(ALLOWED_IMAGE_EXTENSIONS))}."
        )
    if file.size > MAX_IMAGE_SIZE_BYTES:
        raise ValidationError("Image file is too large. Maximum size is 5 MB.")
