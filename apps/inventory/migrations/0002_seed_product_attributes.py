from django.db import migrations

ATTRIBUTES = [
    ("Thread Size", "TEXT", "mm"),
    ("Thread Pitch", "TEXT", "mm"),
    ("Bolt Length", "NUMBER", "mm"),
    ("Bolt Diameter", "NUMBER", "mm"),
    ("Nut Size", "TEXT", "mm"),
    ("Washer Size", "TEXT", "mm"),
    ("Socket Size", "TEXT", "mm"),
    ("Wrench Size", "TEXT", "mm"),
    ("Grade", "TEXT", ""),
    ("Strength Grade", "TEXT", ""),
    ("Fastener Type", "TEXT", ""),
    ("Head Type", "TEXT", ""),
    ("Drive Type", "TEXT", ""),
    ("Voltage", "NUMBER", "V"),
    ("Amperage", "NUMBER", "A"),
    ("Wattage", "NUMBER", "W"),
    ("Resistance", "NUMBER", "ohm"),
    ("Pressure Rating", "NUMBER", "bar"),
    ("Temperature Rating", "NUMBER", "°C"),
    ("Load Capacity", "NUMBER", "kg"),
    ("Rotation Direction", "TEXT", ""),
    ("Number of Teeth", "NUMBER", ""),
    ("Chain Pitch", "TEXT", "mm"),
    ("Belt Length", "NUMBER", "mm"),
    ("Bearing Type", "TEXT", ""),
    ("Inner Diameter", "NUMBER", "mm"),
    ("Outer Diameter", "NUMBER", "mm"),
    ("Seal Type", "TEXT", ""),
    ("Filter Type", "TEXT", ""),
    ("Micron Rating", "NUMBER", "microns"),
    ("Volume", "NUMBER", "L"),
    ("Viscosity Grade", "TEXT", ""),
    ("API Rating", "TEXT", ""),
    ("SAE Grade", "TEXT", ""),
]


def seed_attributes(apps, schema_editor):
    ProductAttribute = apps.get_model("inventory", "ProductAttribute")
    for name, data_type, unit in ATTRIBUTES:
        ProductAttribute.objects.get_or_create(
            normalized_name=name.strip().lower(),
            defaults={"name": name, "data_type": data_type, "unit": unit},
        )


def remove_attributes(apps, schema_editor):
    ProductAttribute = apps.get_model("inventory", "ProductAttribute")
    names = [normalized for normalized, *_ in [(n.strip().lower(),) for n, _, _ in ATTRIBUTES]]
    ProductAttribute.objects.filter(normalized_name__in=names).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_attributes, remove_attributes),
    ]
