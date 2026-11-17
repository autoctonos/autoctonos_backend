"""Revisa las fotos de producto ya subidas contra el estándar de `products/imagenes.py`.

Las fotos nuevas se normalizan al guardarse; las anteriores al estándar no. Este comando
las clasifica:

- **ok** — ya cumplen (cuadradas, JPEG, lado ≤ 1600 px).
- **normalizable** — se pueden llevar al estándar en automático (`--apply` las re-guarda).
- **rehacer** — no hay arreglo automático (muy pequeñas, alargadas, damero de transparencia
  falsa, ilegibles): hay que pedirle al productor otra foto. Se listan con el producto.

Sólo reporta por defecto. Escribe con `--apply`. El archivo viejo queda en el storage
(Cloudinary no se limpia desde aquí): el registro apunta al nuevo.
"""

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from PIL import Image

from products.imagenes import LADO_MAESTRO, validar_imagen_producto
from products.models import ImagenProducto


def _cumple(contenido: bytes) -> bool:
    imagen = Image.open(ContentFile(contenido))
    ancho, alto = imagen.size
    return imagen.format == "JPEG" and ancho == alto and ancho <= LADO_MAESTRO


class Command(BaseCommand):
    help = "Clasifica las fotos de producto según el estándar y normaliza las que se puedan."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply", action="store_true",
            help="Re-guarda normalizadas las fotos «normalizable». Sin esta bandera sólo reporta.",
        )

    def handle(self, *args, apply=False, **options):
        conteo = {"ok": 0, "normalizable": 0, "rehacer": 0}
        imagenes = (
            ImagenProducto.objects.select_related("id_producto")
            .filter(deleted_at__isnull=True)
            .exclude(url_imagen="")
            .exclude(url_imagen__isnull=True)
            .order_by("id_producto__nombre", "id_imagen")
        )
        for registro in imagenes:
            producto = f"{registro.id_producto.nombre} (imagen {registro.id_imagen})"
            try:
                with registro.url_imagen.open("rb") as archivo:
                    contenido = archivo.read()
            except Exception as exc:  # Storage remoto caído, URL de seeder, archivo borrado…
                conteo["rehacer"] += 1
                self.stdout.write(self.style.ERROR(f"rehacer  {producto}: no se pudo leer ({exc})"))
                continue

            nombre = registro.url_imagen.name.rsplit("/", 1)[-1]
            candidato = ContentFile(contenido, name=nombre)
            try:
                validar_imagen_producto(candidato)
            except ValidationError as exc:
                conteo["rehacer"] += 1
                self.stdout.write(self.style.ERROR(f"rehacer  {producto}: {exc.messages[0]}"))
                continue

            if _cumple(contenido):
                conteo["ok"] += 1
                continue

            conteo["normalizable"] += 1
            if apply:
                registro.url_imagen = candidato  # `ImagenProducto.save` lo normaliza.
                registro.save(update_fields=["url_imagen", "updated_at"])
                self.stdout.write(self.style.SUCCESS(f"normalizada  {producto}"))
            else:
                self.stdout.write(f"normalizable  {producto}")

        self.stdout.write(
            f"\nok={conteo['ok']} normalizable={conteo['normalizable']} rehacer={conteo['rehacer']}"
            + ("" if apply else "  (reporte: usa --apply para normalizar)")
        )
