from io import BytesIO

import barcode
from barcode.writer import ImageWriter


def generate_barcode_png(value):
    """Render a Code128 barcode for `value` as PNG bytes, generated in
    memory — never stored as an uploaded file."""
    code128 = barcode.get("code128", value, writer=ImageWriter())
    buffer = BytesIO()
    code128.write(
        buffer,
        options={"write_text": True, "module_height": 10.0, "font_size": 9, "quiet_zone": 2},
    )
    return buffer.getvalue()


def barcode_value_for(product):
    return product.barcode_number or product.sku
