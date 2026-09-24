"""Reporta qué productos publicados todavía no se pueden cotizar.

Sólo lectura. Es el gate operacional antes de encender el cálculo de envíos.
"""

from django.core.management.base import BaseCommand, CommandError

from products.models import Producto


class Command(BaseCommand):
    help = "Lista los productos publicados sin peso, sin origen o con un origen sin cobertura."

    def add_arguments(self, parser):
        parser.add_argument(
            '--todos', action='store_true',
            help="Incluye productos no aprobados o despublicados.",
        )
        parser.add_argument(
            '--strict', action='store_true',
            help="Termina con error si algún producto no es despachable. Para usarlo como gate.",
        )

    def handle(self, *args, **options):
        productos = (
            Producto.objects
            .select_related(
                'id_municipio__id_departamento',
                'id_municipio__cobertura__trayecto_origen',
                'id_productor',
                'id_productor__id_municipio__id_departamento',
                'id_productor__id_municipio__cobertura__trayecto_origen',
            )
            .order_by('nombre')
        )
        if not options['todos']:
            productos = productos.filter(estado='aprobado', deleted_at__isnull=True)

        sin_peso, sin_productor, sin_origen, origen_sin_cobertura, listos = [], [], [], [], 0
        for producto in productos:
            problemas = False
            if producto.peso_kg is None:
                sin_peso.append(producto)
                problemas = True
            if producto.id_productor is None:
                sin_productor.append(producto)
                problemas = True

            # El origen es el override del producto y, si está vacío, el del productor.
            origen = producto.municipio_origen
            if origen is None:
                sin_origen.append(producto)
                problemas = True
            else:
                cobertura = getattr(origen, 'cobertura', None)
                if (cobertura is None or not cobertura.activo
                        or cobertura.trayecto_origen is None or not cobertura.trayecto_origen.activo):
                    origen_sin_cobertura.append(producto)
                    problemas = True
            listos += not problemas

        self._bloque("Sin peso de despacho", sin_peso)
        self._bloque("Sin productor asignado", sin_productor)
        self._bloque("Sin municipio de origen", sin_origen,
                     detalle=lambda p: "" if p.id_productor else " — tampoco tiene productor")
        self._bloque("Origen sin cobertura de envíos", origen_sin_cobertura,
                     detalle=lambda p: f" — {p.municipio_origen}")

        total = len(productos)
        estilo = self.style.SUCCESS if listos == total else self.style.WARNING
        self.stdout.write(estilo(f"\nDespachables: {listos}/{total}"))

        if options['strict'] and listos != total:
            raise CommandError(
                f"{total - listos} producto(s) publicados no se pueden cotizar. "
                "El checkout los rechazaría con un 422."
            )

    def _bloque(self, titulo, productos, detalle=None):
        if not productos:
            self.stdout.write(self.style.SUCCESS(f"{titulo}: ninguno."))
            return
        self.stdout.write(self.style.ERROR(f"{titulo}: {len(productos)}"))
        for producto in productos:
            sufijo = detalle(producto) if detalle else ''
            self.stdout.write(f"  [{producto.id_producto}] {producto.nombre}{sufijo}")
