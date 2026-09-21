"""Crea el Pedido pendiente a partir de una cotización real de `shipping`.

Reusa exactamente el mismo camino que `shipping.views.CotizarView`
(`construir_entrada` + `cotizar`) para que el precio que queda grabado en el Pedido sea
idéntico al que se le mostró/cotizó al comprador. Nunca se confía en precio, flete ni
totales que mande el cliente.
"""

import secrets

from django.db import transaction

from shipping.services.quote import cotizar
from shipping.services.repository import construir_entrada

from ..models import DetallePedido, Envio, Pago, Pedido


def _generar_referencia_payu() -> str:
    """Token opaco, no el PK del Pedido: un id secuencial expuesto en la URL de pago
    filtra cuántos pedidos van (volumen de ventas) a cualquiera que mire la referencia."""
    return f"PEDIDO-{secrets.token_hex(8).upper()}"


@transaction.atomic
def crear_pedido_pendiente(datos: dict) -> tuple[Pedido, Pago]:
    """`datos`: dict con `comprador` (nombre/email/telefono/tipo_documento/documento),
    `id_municipio_destino`, `items` (lista de {id_producto, cantidad}) y `notas` opcional.

    Deja propagar `shipping.services.exceptions.ErrorCotizacion` — la vista la traduce a
    HTTP 422, igual que `CotizarView`.
    """
    comprador = datos['comprador']
    entrada = construir_entrada(datos['id_municipio_destino'], datos['items'])
    resultado = cotizar(entrada)

    pedido = Pedido.objects.create(
        id_usuario=datos.get('id_usuario'),
        comprador_nombre=comprador.get('nombre', ''),
        comprador_email=comprador.get('email', ''),
        comprador_telefono=comprador.get('telefono', ''),
        comprador_tipo_documento=comprador.get('tipo_documento', ''),
        comprador_documento=comprador.get('documento', ''),
        notas=datos.get('notas') or '',
        id_municipio_destino_id=resultado.destino.id_municipio,
        municipio_destino_nombre=resultado.destino.nombre,
        departamento_destino_nombre=resultado.destino.departamento,
        subtotal_productos=resultado.totales.subtotal_productos,
        flete=resultado.totales.flete,
        sobreflete=resultado.totales.sobreflete,
        empaque=resultado.totales.empaque,
        descuento_envio=resultado.totales.descuento_envio,
        envio=resultado.totales.envio,
        total=resultado.totales.total,
        entrega_dias_min=resultado.entrega.dias_min,
        entrega_dias_max=resultado.entrega.dias_max,
    )

    for grupo in resultado.grupos:
        envio = Envio.objects.create(
            id_pedido=pedido,
            id_productor_id=grupo.id_productor,
            id_municipio_origen_id=grupo.id_municipio_origen,
            trayecto_aplicado=grupo.trayecto_aplicado,
            jerarquia=grupo.jerarquia,
            peso_bruto_kg=grupo.peso_bruto_kg,
            peso_facturable_kg=grupo.peso_facturable_kg,
            kilos_adicionales=grupo.kilos_adicionales,
            subtotal=grupo.subtotal,
            valor_kilo_inicial=grupo.valor_kilo_inicial,
            valor_kilo_adicional=grupo.valor_kilo_adicional,
            flete=grupo.flete,
            sobreflete=grupo.sobreflete,
            peso_frio_kg=grupo.peso_frio_kg,
            neveras=grupo.neveras,
            empaque=grupo.empaque,
            total_grupo=grupo.total_grupo,
            entrega_dias_min=grupo.entrega.dias_min,
            entrega_dias_max=grupo.entrega.dias_max,
        )
        for linea in grupo.items:
            DetallePedido.objects.create(
                id_pedido=pedido,
                id_producto_id=linea.id_producto,
                id_envio=envio,
                cantidad=linea.cantidad,
                precio=linea.precio_unitario,
                nombre_producto=linea.nombre,
                peso_unitario_kg=linea.peso_unitario_kg,
                subtotal=linea.subtotal,
                requiere_frio=linea.requiere_frio,
            )

    pago = Pago.objects.create(
        id_pedido=pedido,
        id_usuario=datos.get('id_usuario'),
        metodo_pago='payu',
        estado='pendiente',
        referencia_payu=_generar_referencia_payu(),
        monto=resultado.totales.total,
        moneda='COP',
    )

    return pedido, pago
