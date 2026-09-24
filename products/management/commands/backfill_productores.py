"""Asigna `Producto.id_productor` a partir del campo libre `fabricante`.

`fabricante` es texto que alguien escribió a mano; `Productor` es una fila con municipio,
teléfono y descripción. El emparejamiento se hace por nombre normalizado y **nunca
adivina**: si un fabricante matchea con dos productores, o con ninguno, se reporta y se
deja sin asignar. Un productor equivocado no es un dato feo, es un flete mal cobrado —
el municipio del productor decide la tarifa de origen.

Sólo reporta por defecto. Escribe con `--apply`.
"""

import difflib
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from autoctonos.text import normalizar
from producers.models import Productor
from products.models import Producto

# Fabricantes cuyo texto no normaliza igual que el nombre del productor.
# Clave: `fabricante` normalizado. Valor: nombre del productor tal como está en la DB.
ALIAS_FABRICANTES = {}


class _DryRun(Exception):
    """Aborta la transacción para revertir lo escrito en modo reporte."""


class Command(BaseCommand):
    help = "Empareja el campo libre `fabricante` con `producers.Productor` y asigna la FK."

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply', action='store_true',
            help="Escribe los cambios. Sin esta bandera sólo reporta.",
        )
        parser.add_argument(
            '--todos', action='store_true',
            help="Incluye productos no aprobados y despublicados (por defecto sólo los vivos).",
        )
        parser.add_argument(
            '--alias-file', dest='alias_file', default=None,
            help='JSON {"fabricante normalizado": "Nombre del productor"} con alias extra.',
        )
        parser.add_argument(
            '--reasignar', action='store_true',
            help="Pisa el productor ya asignado. Por defecto sólo toca los que están vacíos.",
        )
        parser.add_argument(
            '--strict', action='store_true',
            help="Termina con error si queda algún producto sin productor. Para usarlo como gate.",
        )

    def handle(self, *args, **options):
        self.apply = options['apply']
        alias = dict(ALIAS_FABRICANTES)
        if options['alias_file']:
            alias.update(self._cargar_alias(Path(options['alias_file'])))

        productores = self._indice_productores()
        if not productores:
            raise CommandError(
                "No hay productores registrados. Créalos en el admin antes de correr el backfill: "
                "este comando empareja, no inventa."
            )

        productos = Producto.objects.select_related('id_productor')
        if not options['todos']:
            productos = productos.filter(estado='aprobado', deleted_at__isnull=True)
        if not options['reasignar']:
            productos = productos.filter(id_productor__isnull=True)

        # Se agrupa por fabricante: son decenas de strings distintos, no miles.
        por_fabricante = {}
        sin_fabricante = []
        for producto in productos:
            if not (producto.fabricante or '').strip():
                sin_fabricante.append(producto)
                continue
            por_fabricante.setdefault(normalizar(producto.fabricante), []).append(producto)

        asignados, ambiguos, sin_match = [], [], []

        try:
            with transaction.atomic():
                for clave, lote in sorted(por_fabricante.items()):
                    candidatos = self._resolver(clave, alias, productores)
                    if len(candidatos) == 1:
                        productor = candidatos[0]
                        Producto.objects.filter(
                            id_producto__in=[p.id_producto for p in lote]
                        ).update(id_productor=productor)
                        asignados.append((clave, lote, productor))
                    elif len(candidatos) > 1:
                        ambiguos.append((clave, lote, candidatos))
                    else:
                        sin_match.append((clave, lote, self._sugerencias(clave, productores)))
                if not self.apply:
                    raise _DryRun()
        except _DryRun:
            pass

        self._reportar(asignados, ambiguos, sin_match, sin_fabricante)

        pendientes = (
            sum(len(lote) for _, lote, _ in ambiguos)
            + sum(len(lote) for _, lote, _ in sin_match)
            + len(sin_fabricante)
        )
        if options['strict'] and pendientes:
            raise CommandError(
                f"Quedan {pendientes} productos sin productor. "
                "Resuélvelos en el admin o con --alias-file antes de desplegar."
            )

    # ------------------------------------------------------------------ índices

    def _cargar_alias(self, ruta):
        if not ruta.exists():
            raise CommandError(f"No existe el archivo de alias: {ruta}")
        with ruta.open(encoding='utf-8') as archivo:
            crudo = json.load(archivo)
        return {normalizar(k): v for k, v in crudo.items()}

    def _indice_productores(self):
        """`{nombre normalizado: [Productor, ...]}`. La lista permite detectar homónimos."""
        indice = {}
        for productor in Productor.objects.select_related('id_municipio'):
            indice.setdefault(normalizar(productor.nombre), []).append(productor)
        return indice

    def _resolver(self, clave, alias, productores):
        if clave in alias:
            return productores.get(normalizar(alias[clave]), [])
        return productores.get(clave, [])

    def _sugerencias(self, clave, productores):
        return difflib.get_close_matches(clave, productores.keys(), n=3, cutoff=0.75)

    # ------------------------------------------------------------------ reporte

    def _reportar(self, asignados, ambiguos, sin_match, sin_fabricante):
        total_asignados = sum(len(lote) for _, lote, _ in asignados)

        if asignados:
            self.stdout.write(self.style.SUCCESS("\nEmparejados"))
            for clave, lote, productor in asignados:
                municipio = productor.id_municipio or "SIN MUNICIPIO"
                self.stdout.write(
                    f"  {clave!r} · {len(lote)} producto(s) → {productor.nombre} ({municipio})"
                )
                if productor.id_municipio is None:
                    self.stdout.write(self.style.WARNING(
                        f"    ojo: {productor.nombre} no tiene municipio, sus productos no cotizarán."
                    ))

        if ambiguos:
            self.stdout.write(self.style.ERROR("\nAmbiguos (no se asignó nada)"))
            for clave, lote, candidatos in ambiguos:
                nombres = ", ".join(f"#{p.id_productor} {p.nombre}" for p in candidatos)
                self.stdout.write(f"  {clave!r} · {len(lote)} producto(s) → {nombres}")

        if sin_match:
            self.stdout.write(self.style.ERROR("\nSin pareja"))
            for clave, lote, sugerencias in sin_match:
                extra = f"  ¿será {', '.join(sugerencias)}?" if sugerencias else ""
                self.stdout.write(f"  {clave!r} · {len(lote)} producto(s){extra}")

        if sin_fabricante:
            self.stdout.write(self.style.ERROR("\nSin fabricante escrito"))
            for producto in sin_fabricante[:20]:
                self.stdout.write(f"  #{producto.id_producto} {producto.nombre}")
            if len(sin_fabricante) > 20:
                self.stdout.write(f"  … y {len(sin_fabricante) - 20} más")

        pendientes = (
            sum(len(lote) for _, lote, _ in ambiguos)
            + sum(len(lote) for _, lote, _ in sin_match)
            + len(sin_fabricante)
        )
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Asignados: {total_asignados} · Pendientes: {pendientes}"
        ))
        if not self.apply:
            self.stdout.write(self.style.WARNING(
                "Modo reporte: no se escribió nada. Corre con --apply para aplicar."
            ))
