"""`Categoria.slug`: dirección pública /categories/<slug>.

En tres pasos porque el campo es único y ya hay filas: se agrega sin unicidad, se llena
desde el nombre (con sufijo -2, -3… si dos nombres dan el mismo slug) y recién ahí se
vuelve único.
"""

from django.db import migrations, models
from django.utils.text import slugify

import products.models


def llenar_slugs(apps, schema_editor):
    Categoria = apps.get_model("products", "Categoria")
    usados = set()
    for categoria in Categoria.objects.order_by("id_categoria"):
        base = slugify(categoria.nombre)[:100] or "categoria"
        candidato, n = base, 2
        while candidato in usados:
            candidato, n = f"{base}-{n}", n + 1
        usados.add(candidato)
        categoria.slug = candidato
        categoria.save(update_fields=["slug"])


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0013_imagenproducto_estandar_foto"),
    ]

    operations = [
        migrations.AddField(
            model_name="categoria",
            name="slug",
            field=models.SlugField(blank=True, default="", max_length=110, db_index=False),
            preserve_default=False,
        ),
        migrations.RunPython(llenar_slugs, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="categoria",
            name="slug",
            field=models.SlugField(
                blank=True,
                help_text="Minúsculas y guiones, ej. lacteos-quesos → /categories/lacteos-quesos. "
                          "Vacío = se genera del nombre.",
                max_length=110,
                unique=True,
                validators=[products.models.validar_slug_categoria],
                verbose_name="Dirección (URL)",
            ),
        ),
    ]
