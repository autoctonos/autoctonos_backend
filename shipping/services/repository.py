"""Único puente entre el ORM y el servicio de cálculo.

El cliente sólo manda ids y cantidades: precios, pesos y orígenes se resuelven aquí.
"""

from products.models import Producto
from shipping.models import CoberturaMunicipio, ConfiguracionEmpaque, PromocionEnvio

from .exceptions import (
    CarritoVacio,
    DestinoNoSoportado,
    EmpaqueNoConfigurado,
    OrigenNoSoportado,
    ProductoNoDisponible,
    ProductoSinOrigen,
    ProductoSinPeso,
    ProductoSinProductor,
)
from .quote import (
    ConfigEmpaque,
    Destino,
    EntradaCotizacion,
    ItemCotizacion,
    ParametrosCalculo,
    PromocionCalculo,
    TarifaTrayecto,
)


def _tarifa(trayecto) -> TarifaTrayecto:
    return TarifaTrayecto(
        codigo=trayecto.codigo,
        nombre=trayecto.nombre,
        jerarquia=trayecto.jerarquia,
        valor_kilo_inicial=trayecto.valor_kilo_inicial,
        valor_kilo_adicional=trayecto.valor_kilo_adicional,
        sobreflete_minimo=trayecto.sobreflete_minimo,
        porcentaje_sobreflete=trayecto.porcentaje_sobreflete,
        dias_entrega_min=trayecto.dias_entrega_min,
        dias_entrega_max=trayecto.dias_entrega_max,
    )


def _resolver_destino(id_municipio_destino: int) -> Destino:
    cobertura = (
        CoberturaMunicipio.objects
        .select_related('municipio__id_departamento', 'trayecto_destino')
        .filter(municipio_id=id_municipio_destino, activo=True, trayecto_destino__isnull=False,
                trayecto_destino__activo=True)
        .first()
    )
    if cobertura is None:
        raise DestinoNoSoportado(
            "Aún no realizamos envíos a este municipio.",
            {'id_municipio_destino': id_municipio_destino},
        )
    municipio = cobertura.municipio
    return Destino(
        id_municipio=municipio.id_municipio,
        nombre=municipio.nombre,
        departamento=municipio.id_departamento.nombre,
        tarifa=_tarifa(cobertura.trayecto_destino),
    )


def _resolver_items(solicitados) -> tuple[ItemCotizacion, ...]:
    """`solicitados`: iterable de dicts con `id_producto` y `cantidad`."""
    cantidades = {int(s['id_producto']): int(s['cantidad']) for s in solicitados}
    if not cantidades:
        raise CarritoVacio("El carrito está vacío.")

    productos = {
        p.id_producto: p
        for p in Producto.objects
        .select_related('id_categoria',
                        'id_municipio__id_departamento',
                        'id_municipio__cobertura__trayecto_origen',
                        'id_productor',
                        'id_productor__id_municipio__id_departamento',
                        'id_productor__id_municipio__cobertura__trayecto_origen')
        .filter(id_producto__in=cantidades.keys(), estado='aprobado', deleted_at__isnull=True)
    }

    items = []
    for id_producto, cantidad in cantidades.items():
        producto = productos.get(id_producto)
        if producto is None:
            raise ProductoNoDisponible(
                "Uno de los productos del carrito ya no está disponible.",
                {'id_producto': id_producto},
            )
        if producto.peso_kg is None:
            raise ProductoSinPeso(
                f"El producto «{producto.nombre}» aún no tiene peso de despacho registrado.",
                {'id_producto': id_producto, 'nombre': producto.nombre},
            )
        productor = producto.id_productor
        if productor is None:
            raise ProductoSinProductor(
                f"El producto «{producto.nombre}» todavía no está asociado a un productor.",
                {'id_producto': id_producto, 'nombre': producto.nombre},
            )

        # El origen es el override del producto y, si está vacío, el del productor.
        municipio = producto.municipio_origen
        if municipio is None:
            raise ProductoSinOrigen(
                f"El producto «{producto.nombre}» no tiene municipio de origen: ni el "
                f"producto ni el productor «{productor.nombre}» lo tienen registrado.",
                {'id_producto': id_producto, 'nombre': producto.nombre,
                 'id_productor': productor.id_productor, 'productor': productor.nombre},
            )

        cobertura = getattr(municipio, 'cobertura', None)
        if (cobertura is None or not cobertura.activo
                or cobertura.trayecto_origen is None or not cobertura.trayecto_origen.activo):
            raise OrigenNoSoportado(
                f"Todavía no despachamos desde {municipio.nombre} "
                f"({municipio.id_departamento.nombre}).",
                {'id_producto': id_producto, 'id_municipio_origen': municipio.id_municipio,
                 'municipio_origen': municipio.nombre},
            )

        items.append(ItemCotizacion(
            id_producto=producto.id_producto,
            nombre=producto.nombre,
            cantidad=cantidad,
            precio_unitario=producto.precio_con_descuento(),
            peso_unitario_kg=producto.peso_kg,
            requiere_frio=producto.requiere_frio,
            id_productor=productor.id_productor,
            productor=productor.nombre,
            id_municipio_origen=municipio.id_municipio,
            municipio_origen=municipio.nombre,
            departamento_origen=municipio.id_departamento.nombre,
            tarifa_origen=_tarifa(cobertura.trayecto_origen),
        ))
    return tuple(items)


def _resolver_config_empaque() -> ConfigEmpaque:
    config = ConfiguracionEmpaque.objects.filter(activo=True).first()
    if config is None:
        raise EmpaqueNoConfigurado(
            "El costo de empaque refrigerado no está configurado.", {},
        )
    return ConfigEmpaque(capacidad_kg=config.capacidad_kg, costo_nevera=config.costo_nevera)


def _resolver_parametros() -> ParametrosCalculo:
    promocion = PromocionEnvio.objects.filter(activo=True).first()
    if promocion is None:
        return ParametrosCalculo()
    return ParametrosCalculo(promocion=PromocionCalculo(
        umbral_subtotal=promocion.umbral_subtotal,
        jerarquia_maxima_cubierta=promocion.jerarquia_maxima_cubierta,
        tope_cubierto=promocion.tope_cubierto,
        cubre_empaque=promocion.cubre_empaque,
    ))


def construir_entrada(id_municipio_destino: int, items_solicitados) -> EntradaCotizacion:
    return EntradaCotizacion(
        destino=_resolver_destino(id_municipio_destino),
        items=_resolver_items(items_solicitados),
        config_empaque=_resolver_config_empaque(),
        parametros=_resolver_parametros(),
    )


def destinos_por_departamento():
    """Municipios habilitados como destino, agrupados por departamento."""
    coberturas = (
        CoberturaMunicipio.objects
        .select_related('municipio__id_departamento', 'trayecto_destino')
        .filter(activo=True, trayecto_destino__isnull=False, trayecto_destino__activo=True)
        .order_by('municipio__id_departamento__nombre', 'municipio__nombre')
    )

    departamentos = {}
    version = None
    for cobertura in coberturas:
        municipio = cobertura.municipio
        departamento = municipio.id_departamento
        entrada = departamentos.setdefault(departamento.id_departamento, {
            'id_departamento': departamento.id_departamento,
            'nombre': departamento.nombre,
            'municipios': [],
        })
        entrada['municipios'].append({
            'id_municipio': municipio.id_municipio,
            'nombre': municipio.nombre,
            'trayecto': cobertura.trayecto_destino.codigo,
            'jerarquia': cobertura.trayecto_destino.jerarquia,
        })
        if version is None or cobertura.updated_at > version:
            version = cobertura.updated_at

    return list(departamentos.values()), version
