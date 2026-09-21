"""Cálculo de flete, sobreflete y empaque refrigerado.

Módulo puro: sin ORM, sin DRF, sin dependencias de Django. Todo el dinero es Decimal.
"""

from dataclasses import dataclass, field
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal
from itertools import groupby

CENTAVO = Decimal('0.01')
GRAMO = Decimal('0.001')
CERO = Decimal('0')


def _money(valor: Decimal) -> Decimal:
    return valor.quantize(CENTAVO, rounding=ROUND_HALF_UP)


def _kilos(valor: Decimal) -> Decimal:
    return valor.quantize(GRAMO, rounding=ROUND_HALF_UP)


def kilos_adicionales(peso_facturable: int) -> int:
    """Kilos que se cobran a tarifa adicional.

    El tarifario vigente usa `SI(peso>=1; peso-1; peso)`: un envío de exactamente 1 kg no
    paga adicional. (La versión anterior de la hoja usaba `>`, que sí lo cobraba.)
    """
    return peso_facturable - 1 if peso_facturable > 1 else 0


# --------------------------------------------------------------------------- entrada

@dataclass(frozen=True)
class EntregaEstimada:
    """Rango de días hábiles. Sale de la hoja «Convenciones» del tarifario."""
    dias_min: int
    dias_max: int


@dataclass(frozen=True)
class TarifaTrayecto:
    codigo: str
    nombre: str
    jerarquia: int
    valor_kilo_inicial: Decimal
    valor_kilo_adicional: Decimal
    sobreflete_minimo: Decimal
    porcentaje_sobreflete: Decimal
    dias_entrega_min: int
    dias_entrega_max: int


@dataclass(frozen=True)
class ItemCotizacion:
    id_producto: int
    nombre: str
    cantidad: int
    precio_unitario: Decimal
    peso_unitario_kg: Decimal
    requiere_frio: bool
    id_productor: int
    productor: str
    id_municipio_origen: int
    municipio_origen: str
    departamento_origen: str
    tarifa_origen: TarifaTrayecto


@dataclass(frozen=True)
class ConfigEmpaque:
    capacidad_kg: Decimal
    costo_nevera: Decimal


@dataclass(frozen=True)
class PromocionCalculo:
    """Envío gratis por monto. Cubre flete y, si se marca, empaque.

    El sobreflete queda fuera a propósito: es la garantía del producto, no un costo de
    transporte, y siempre se cobra.
    """
    umbral_subtotal: Decimal
    jerarquia_maxima_cubierta: int | None = None
    tope_cubierto: Decimal | None = None
    cubre_empaque: bool = False


@dataclass(frozen=True)
class ParametrosCalculo:
    promocion: PromocionCalculo | None = None


@dataclass(frozen=True)
class Destino:
    id_municipio: int
    nombre: str
    departamento: str
    tarifa: TarifaTrayecto


@dataclass(frozen=True)
class EntradaCotizacion:
    destino: Destino
    items: tuple[ItemCotizacion, ...]
    config_empaque: ConfigEmpaque
    parametros: ParametrosCalculo = field(default_factory=ParametrosCalculo)


# --------------------------------------------------------------------------- salida

@dataclass(frozen=True)
class LineaCotizada:
    id_producto: int
    nombre: str
    cantidad: int
    precio_unitario: Decimal
    peso_unitario_kg: Decimal
    subtotal: Decimal
    requiere_frio: bool


@dataclass(frozen=True)
class GrupoEnvio:
    """Una guía: todo lo que un productor despacha desde un mismo municipio."""
    id_productor: int
    productor: str
    id_municipio_origen: int
    municipio_origen: str
    departamento_origen: str
    trayecto_aplicado: str
    jerarquia: int
    entrega: EntregaEstimada
    items: tuple[LineaCotizada, ...]
    peso_bruto_kg: Decimal
    peso_facturable_kg: int
    kilos_adicionales: int
    subtotal: Decimal
    valor_kilo_inicial: Decimal
    valor_kilo_adicional: Decimal
    flete: Decimal
    sobreflete: Decimal
    peso_frio_kg: Decimal
    neveras: int
    empaque: Decimal
    total_grupo: Decimal


@dataclass(frozen=True)
class ResultadoPromocion:
    aplicada: bool
    umbral: Decimal | None
    descuento: Decimal


@dataclass(frozen=True)
class TotalesCotizacion:
    subtotal_productos: Decimal
    flete: Decimal
    sobreflete: Decimal
    empaque: Decimal
    descuento_envio: Decimal
    envio: Decimal
    total: Decimal


@dataclass(frozen=True)
class ResultadoCotizacion:
    destino: Destino
    grupos: tuple[GrupoEnvio, ...]
    entrega: EntregaEstimada
    promocion: ResultadoPromocion
    totales: TotalesCotizacion


# --------------------------------------------------------------------------- cálculo

def _tarifa_aplicada(tarifa_origen: TarifaTrayecto, tarifa_destino: TarifaTrayecto) -> TarifaTrayecto:
    return tarifa_destino if tarifa_destino.jerarquia >= tarifa_origen.jerarquia else tarifa_origen


def _clave_grupo(item: ItemCotizacion) -> tuple[int, int]:
    """Una guía por productor y municipio de despacho.

    El productor es el criterio de negocio: sus productos viajan juntos y se tarifan sobre
    el peso y el subtotal sumados. El municipio entra en la clave porque la tarifa depende
    de él: si un productor despacha un producto desde un municipio distinto al suyo
    (override en `Producto.id_municipio`), son dos recogidas y dos fletes. Sin el
    municipio en la clave, `_cotizar_grupo` tomaría la tarifa del primer ítem del carrito
    y el precio dependería del orden en que el cliente agregó las cosas.
    """
    return (item.id_productor, item.id_municipio_origen)


def _orden_grupo(item: ItemCotizacion) -> tuple[str, int, int]:
    """Orden estable y legible: alfabético por productor, con el id como desempate de
    homónimos. `productor` está determinado por `id_productor` (salen de la misma fila),
    así que ordenar por nombre deja adyacentes los ítems de una misma clave."""
    return (item.productor.casefold(), *_clave_grupo(item))


def _cotizar_grupo(items: tuple[ItemCotizacion, ...], destino: Destino,
                   config_empaque: ConfigEmpaque) -> GrupoEnvio:
    referencia = items[0]
    if any(_clave_grupo(item) != _clave_grupo(referencia) for item in items):
        raise ValueError("Un grupo de envío no puede mezclar productores ni municipios de origen.")
    tarifa = _tarifa_aplicada(referencia.tarifa_origen, destino.tarifa)

    lineas = tuple(
        LineaCotizada(
            id_producto=item.id_producto,
            nombre=item.nombre,
            cantidad=item.cantidad,
            precio_unitario=_money(item.precio_unitario),
            peso_unitario_kg=_kilos(item.peso_unitario_kg),
            subtotal=_money(item.precio_unitario * item.cantidad),
            requiere_frio=item.requiere_frio,
        )
        for item in items
    )

    subtotal = _money(sum((linea.subtotal for linea in lineas), CERO))
    peso_bruto = sum((item.peso_unitario_kg * item.cantidad for item in items), CERO)
    peso_facturable = int(peso_bruto.to_integral_value(rounding=ROUND_CEILING))
    adicionales = kilos_adicionales(peso_facturable)

    flete = _money(tarifa.valor_kilo_inicial + adicionales * tarifa.valor_kilo_adicional)
    # Base del 2%: el SUBTOTAL DEL PRODUCTO (hoja «Módulo de Compra», F15 = IF((F7*0.02)
    # <800;800;F7*0.02), donde F7 es "Valor Subtotal"), no el flete (F14). Con montos
    # bajos ambas bases caen en el piso de $800 y parecen coincidir — no es así: son
    # fórmulas distintas, verificado contra el .xlsx original celda por celda.
    sobreflete = _money(max(tarifa.sobreflete_minimo, subtotal * tarifa.porcentaje_sobreflete))

    peso_frio = sum(
        (item.peso_unitario_kg * item.cantidad for item in items if item.requiere_frio), CERO
    )
    if peso_frio > CERO and config_empaque.capacidad_kg > CERO:
        neveras = int((peso_frio / config_empaque.capacidad_kg).to_integral_value(rounding=ROUND_CEILING))
    else:
        neveras = 0
    empaque = _money(neveras * config_empaque.costo_nevera)

    return GrupoEnvio(
        id_productor=referencia.id_productor,
        productor=referencia.productor,
        id_municipio_origen=referencia.id_municipio_origen,
        municipio_origen=referencia.municipio_origen,
        departamento_origen=referencia.departamento_origen,
        trayecto_aplicado=tarifa.codigo,
        jerarquia=tarifa.jerarquia,
        # Los días salen de la tarifa aplicada, igual que el flete: `XLOOKUP(F12, ...)`.
        entrega=EntregaEstimada(tarifa.dias_entrega_min, tarifa.dias_entrega_max),
        items=lineas,
        peso_bruto_kg=_kilos(peso_bruto),
        peso_facturable_kg=peso_facturable,
        kilos_adicionales=adicionales,
        subtotal=subtotal,
        valor_kilo_inicial=_money(tarifa.valor_kilo_inicial),
        valor_kilo_adicional=_money(tarifa.valor_kilo_adicional),
        flete=flete,
        sobreflete=sobreflete,
        peso_frio_kg=_kilos(peso_frio),
        neveras=neveras,
        empaque=empaque,
        total_grupo=_money(subtotal + flete + sobreflete + empaque),
    )


def _descuento_promocion(promocion: PromocionCalculo | None, grupos: tuple[GrupoEnvio, ...],
                         subtotal_productos: Decimal) -> Decimal:
    if promocion is None or subtotal_productos < promocion.umbral_subtotal:
        return CERO

    cubierto = CERO
    for grupo in grupos:
        if (promocion.jerarquia_maxima_cubierta is not None
                and grupo.jerarquia > promocion.jerarquia_maxima_cubierta):
            continue
        # Sólo el flete: el sobreflete es la garantía del producto y nunca se descuenta.
        cubierto += grupo.flete
        if promocion.cubre_empaque:
            cubierto += grupo.empaque

    if promocion.tope_cubierto is not None:
        cubierto = min(cubierto, promocion.tope_cubierto)
    return _money(cubierto)


def _entrega_global(grupos: tuple[GrupoEnvio, ...]) -> EntregaEstimada:
    """Cuándo está completo el pedido: cuando llega el último paquete.

    Por eso los dos extremos son máximos. Con grupos de 1-1 y 8-10 el rango correcto es
    8-10, no 1-10: es imposible tener todo en un día.
    """
    return EntregaEstimada(
        dias_min=max(grupo.entrega.dias_min for grupo in grupos),
        dias_max=max(grupo.entrega.dias_max for grupo in grupos),
    )


def cotizar(entrada: EntradaCotizacion) -> ResultadoCotizacion:
    """Cotiza un carrito. Un grupo de envío por productor y municipio de origen."""
    if not entrada.items:
        raise ValueError("La cotización requiere al menos un item.")

    ordenados = sorted(entrada.items, key=_orden_grupo)
    grupos = tuple(
        _cotizar_grupo(tuple(items), entrada.destino, entrada.config_empaque)
        for _, items in groupby(ordenados, key=_clave_grupo)
    )

    subtotal_productos = _money(sum((grupo.subtotal for grupo in grupos), CERO))
    flete = _money(sum((grupo.flete for grupo in grupos), CERO))
    sobreflete = _money(sum((grupo.sobreflete for grupo in grupos), CERO))
    empaque = _money(sum((grupo.empaque for grupo in grupos), CERO))

    promocion = entrada.parametros.promocion
    descuento = _descuento_promocion(promocion, grupos, subtotal_productos)
    envio = _money(max(CERO, flete + sobreflete + empaque - descuento))

    return ResultadoCotizacion(
        destino=entrada.destino,
        grupos=grupos,
        entrega=_entrega_global(grupos),
        promocion=ResultadoPromocion(
            aplicada=descuento > CERO,
            umbral=_money(promocion.umbral_subtotal) if promocion else None,
            descuento=descuento,
        ),
        totales=TotalesCotizacion(
            subtotal_productos=subtotal_productos,
            flete=flete,
            sobreflete=sobreflete,
            empaque=empaque,
            descuento_envio=descuento,
            envio=envio,
            total=_money(subtotal_productos + envio),
        ),
    )
