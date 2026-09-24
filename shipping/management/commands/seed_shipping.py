"""Siembra el tarifario y la cobertura de municipios desde shipping/data/*.json.

Estricto por defecto: si un municipio del archivo no encuentra pareja en
`locations.Municipio`, la corrida entera se revierte. Una cobertura parcial dejaría el
checkout sin destinos sin que nadie se entere.
"""

import difflib
import json
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from autoctonos.text import normalizar
from locations.models import Municipio
from shipping.models import CoberturaMunicipio, ConfiguracionEmpaque, PromocionEnvio, Trayecto

DATA_DIR = Path(__file__).resolve().parents[2] / 'data'

# El .xlsx y api-colombia.com nombran distinto los mismos municipios.
# Clave: (municipio, departamento) normalizados del archivo.
# Valor: pares candidatos (municipio, departamento) en la DB; `None` conserva el del archivo.
ALIAS_MUNICIPIOS = {
    # api-colombia guarda Bogotá como su propio departamento.
    ('bogota d.c.', 'cundinamarca'): [
        ('bogota d.c.', 'bogota'),
        ('bogota d.c.', 'bogota d.c.'),
        ('bogota', 'bogota'),
        ('bogota', 'bogota d.c.'),
    ],
    ('san juan de pasto', 'narino'): [('pasto', None)],
    ('cartagena de indias', 'bolivar'): [('cartagena', None), ('cartagena de indias', None)],
    ('san jose de cucuta', 'norte de santander'): [('cucuta', None)],
    # Nombres oficiales nuevos; api-colombia todavía usa los antiguos.
    ('guican', 'boyaca'): [('guican de la sierra', None)],
    ('guican de la sierra', 'boyaca'): [('guican', None)],
    ('villa de leyva', 'boyaca'): [('villa de leiva', None)],
    ('villa de leiva', 'boyaca'): [('villa de leyva', None)],
    ('buenavista', 'boyaca'): [('buena vista', None)],
    ('buena vista', 'boyaca'): [('buenavista', None)],
    ('san andres', 'san andres, providencia y santa catalina'): [
        ('san andres', 'san andres y providencia'),
        ('san andres', 'archipielago de san andres, providencia y santa catalina'),
    ],
}

# Nombres de departamento que difieren entre el archivo y la DB.
ALIAS_DEPARTAMENTOS = {
    'san andres, providencia y santa catalina': 'san andres y providencia',
    'archipielago de san andres, providencia y santa catalina': 'san andres y providencia',
}


# `normalizar` se importa de `autoctonos.text`; se re-exporta aquí porque los tests y los
# alias de este módulo la usan por nombre.
__all__ = ['normalizar', 'ALIAS_MUNICIPIOS', 'ALIAS_DEPARTAMENTOS', 'Command']


class Command(BaseCommand):
    help = "Siembra trayectos, cobertura de municipios, empaque y promoción de envío."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help="No escribe nada. Reporta lo que haría y sugiere alias para lo que no matchea.",
        )
        parser.add_argument(
            '--file', dest='archivo_cobertura', default=None,
            help="Ruta alterna al JSON de cobertura.",
        )
        parser.add_argument(
            '--allow-missing', action='store_true',
            help="Continúa aunque haya municipios sin pareja en locations.Municipio.",
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.allow_missing = options['allow_missing']

        tarifario = self._cargar(DATA_DIR / 'tarifario.json')
        cobertura = self._cargar(Path(options['archivo_cobertura']) if options['archivo_cobertura']
                                else DATA_DIR / 'cobertura.json')

        try:
            with transaction.atomic():
                trayectos = self._sembrar_trayectos(tarifario)
                self._sembrar_cobertura(cobertura, trayectos)
                self._sembrar_empaque()
                self._sembrar_promocion()
                if self.dry_run:
                    raise _DryRun()
        except _DryRun:
            self.stdout.write(self.style.WARNING("Dry-run: no se escribió nada."))

    # ------------------------------------------------------------------ carga

    def _cargar(self, ruta):
        if not ruta.exists():
            raise CommandError(f"No existe el archivo de datos: {ruta}")
        with ruta.open(encoding='utf-8') as archivo:
            return json.load(archivo)

    # -------------------------------------------------------------- trayectos

    def _sembrar_trayectos(self, filas):
        trayectos = {}
        for fila in filas:
            faltantes = [c for c in ('dias_entrega_min', 'dias_entrega_max') if c not in fila]
            if faltantes:
                raise CommandError(
                    f"El tarifario no trae {' ni '.join(faltantes)} para «{fila['codigo']}». "
                    "Actualiza shipping/data/tarifario.json con la hoja «Convenciones»."
                )
            trayecto, creado = Trayecto.objects.update_or_create(
                codigo=fila['codigo'],
                defaults={
                    'nombre': fila['nombre'],
                    'jerarquia': fila['jerarquia'],
                    'valor_kilo_inicial': Decimal(fila['valor_kilo_inicial']),
                    'valor_kilo_adicional': Decimal(fila['valor_kilo_adicional']),
                    'sobreflete_minimo': Decimal(fila['sobreflete_minimo']),
                    'porcentaje_sobreflete': Decimal(fila['porcentaje_sobreflete']),
                    'dias_entrega_min': int(fila['dias_entrega_min']),
                    'dias_entrega_max': int(fila['dias_entrega_max']),
                    'activo': True,
                },
            )
            trayectos[fila['codigo']] = trayecto
            self._log(f"Trayecto {'creado' if creado else 'actualizado'}: {trayecto.nombre}")
        self.stdout.write(self.style.SUCCESS(f"Trayectos: {len(trayectos)}"))
        return trayectos

    # --------------------------------------------------------------- cobertura

    def _indice_municipios(self):
        """Una sola query. Devuelve el índice por (municipio, departamento) y el
        índice por municipio con los ambiguos marcados."""
        por_par = {}
        por_nombre = {}
        for municipio in Municipio.objects.select_related('id_departamento'):
            nombre = normalizar(municipio.nombre)
            departamento = normalizar(municipio.id_departamento.nombre)
            por_par[(nombre, departamento)] = municipio
            por_nombre.setdefault(nombre, []).append(municipio)
        return por_par, por_nombre

    def _resolver_municipio(self, fila, por_par, por_nombre):
        nombre = normalizar(fila['municipio'])
        departamento = normalizar(fila['departamento'])

        for nombre_alias, departamento_alias in ALIAS_MUNICIPIOS.get((nombre, departamento), []):
            candidato = por_par.get((nombre_alias, departamento_alias or departamento))
            if candidato is not None:
                return candidato

        departamento_alias = ALIAS_DEPARTAMENTOS.get(departamento, departamento)
        for clave in {(nombre, departamento), (nombre, departamento_alias)}:
            candidato = por_par.get(clave)
            if candidato is not None:
                return candidato

        homonimos = por_nombre.get(nombre, [])
        if len(homonimos) == 1:
            municipio = homonimos[0]
            self.stdout.write(self.style.WARNING(
                f"  {fila['municipio']} ({fila['departamento']}) se resolvió por nombre único "
                f"a {municipio}; el departamento no coincide."
            ))
            return municipio
        return None

    def _sugerencia(self, fila, por_nombre):
        candidatos = difflib.get_close_matches(normalizar(fila['municipio']), por_nombre.keys(), n=3, cutoff=0.75)
        if not candidatos:
            return "sin candidatos parecidos"
        return "; ".join(str(por_nombre[c][0]) for c in candidatos)

    def _sembrar_cobertura(self, filas, trayectos):
        por_par, por_nombre = self._indice_municipios()

        resueltos = []
        faltantes = []
        for fila in filas:
            municipio = self._resolver_municipio(fila, por_par, por_nombre)
            if municipio is None:
                faltantes.append(fila)
            else:
                resueltos.append((fila, municipio))

        if faltantes:
            for fila in faltantes:
                mensaje = f"  Sin pareja: {fila['municipio']} ({fila['departamento']})"
                if self.dry_run:
                    mensaje += f" → ¿{self._sugerencia(fila, por_nombre)}?"
                self.stdout.write(self.style.ERROR(mensaje))
            if not self.allow_missing:
                raise CommandError(
                    f"{len(faltantes)} municipios del archivo no existen en locations.Municipio. "
                    "Corre `seed_locations` primero, agrega el alias que falte, o usa --allow-missing."
                )

        vistos = set()
        creados = actualizados = 0
        for fila, municipio in resueltos:
            if municipio.id_municipio in vistos:
                raise CommandError(
                    f"El municipio {municipio} quedó asociado a dos filas del archivo "
                    f"(la última: {fila['municipio']} / {fila['departamento']})."
                )
            vistos.add(municipio.id_municipio)

            distancia = fila.get('distancia_km_tunja')
            _, creado = CoberturaMunicipio.objects.update_or_create(
                municipio=municipio,
                defaults={
                    'trayecto_origen': trayectos.get(fila.get('trayecto_origen')),
                    'trayecto_destino': trayectos.get(fila.get('trayecto_destino')),
                    'provincia': fila.get('provincia') or '',
                    'distancia_km_tunja': Decimal(str(distancia)) if distancia is not None else None,
                    'activo': True,
                },
            )
            creados += creado
            actualizados += not creado

        retirados = CoberturaMunicipio.objects.exclude(municipio_id__in=vistos).update(activo=False)
        self.stdout.write(self.style.SUCCESS(
            f"Cobertura: {creados} creados, {actualizados} actualizados, {retirados} desactivados."
        ))

    # ------------------------------------------------------- empaque/promoción

    def _sembrar_empaque(self):
        _, creado = ConfiguracionEmpaque.objects.get_or_create(
            activo=True,
            defaults={'capacidad_kg': Decimal('6.000'), 'costo_nevera': Decimal('12000.00')},
        )
        self.stdout.write(self.style.SUCCESS(
            "Empaque: configuración creada." if creado
            else "Empaque: ya existía, se respeta lo configurado en el admin."
        ))

    def _sembrar_promocion(self):
        _, creado = PromocionEnvio.objects.get_or_create(
            activo=True,
            defaults={
                'umbral_subtotal': Decimal('200000.00'),
                'jerarquia_maxima_cubierta': None,
                'tope_cubierto': None,
                'cubre_sobreflete': True,
                'cubre_empaque': False,
            },
        )
        self.stdout.write(self.style.SUCCESS(
            "Promoción: creada replicando el envío gratis actual." if creado
            else "Promoción: ya existía, se respeta lo configurado en el admin."
        ))

    def _log(self, mensaje):
        if self.dry_run:
            self.stdout.write(f"  {mensaje}")


class _DryRun(Exception):
    """Aborta la transacción al final de un dry-run."""
