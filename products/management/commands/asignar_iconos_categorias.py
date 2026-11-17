"""Asigna un ícono Lucide con sentido a las categorías que todavía no tienen uno.

Las categorías creadas antes del selector de íconos quedaron en «Automático». Este comando
las empareja por nombre normalizado con `SUGERENCIAS` y, con `--apply`, descarga y congela
el SVG igual que el admin (`descargar_svg` → `Categoria.icono_svg`).

**Nunca pisa un ícono elegido en el admin**: sólo toca categorías con `icono` vacío.
Las que no están en el mapa se reportan y quedan con el ícono neutro de la tienda.

Sólo reporta por defecto. Escribe con `--apply`. Necesita salida a internet (Iconify).
"""

from django.core.management.base import BaseCommand

from autoctonos.text import normalizar
from products.iconos import IconoError, descargar_svg
from products.models import Categoria

# Clave: nombre normalizado (sin tildes, minúsculas). Valor: slug Lucide en Iconify.
SUGERENCIAS = {
    "amasijos": "croissant",
    "artesanias": "palette",
    "bebidas": "cup-soda",
    "cafe": "coffee",
    "cesteria": "shopping-basket",
    "colaciones": "candy",
    "dulces": "candy",
    "embutidos y encurtidos": "ham",
    "embutidos": "ham",
    "frutas": "apple",
    "lacteos": "milk",
    "miel": "flower",
    "muebles": "armchair",
    "quesos": "cheese",
    "salud": "heart-pulse",
    "tejidos": "spool",
    "verduras": "carrot",
}


class Command(BaseCommand):
    help = "Asigna íconos Lucide a categorías sin ícono, según su nombre."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply", action="store_true",
            help="Descarga los SVG y guarda. Sin esta bandera sólo reporta.",
        )

    def handle(self, *args, apply=False, **options):
        asignadas = sin_sugerencia = errores = 0
        for categoria in Categoria.objects.filter(icono="").order_by("nombre"):
            slug = SUGERENCIAS.get(normalizar(categoria.nombre))
            if not slug:
                sin_sugerencia += 1
                self.stdout.write(f"sin sugerencia  {categoria.nombre} (elígelo en el admin)")
                continue
            if not apply:
                self.stdout.write(f"asignaría  {categoria.nombre} → {slug}")
                asignadas += 1
                continue
            try:
                svg = descargar_svg(slug)
            except IconoError as exc:
                errores += 1
                self.stdout.write(self.style.ERROR(f"error  {categoria.nombre} → {slug}: {exc}"))
                continue
            categoria.icono, categoria.icono_svg = slug, svg
            categoria.save(update_fields=["icono", "icono_svg"])
            asignadas += 1
            self.stdout.write(self.style.SUCCESS(f"asignado  {categoria.nombre} → {slug}"))

        self.stdout.write(
            f"\nasignadas={asignadas} sin_sugerencia={sin_sugerencia} errores={errores}"
            + ("" if apply else "  (reporte: usa --apply para guardar)")
        )
