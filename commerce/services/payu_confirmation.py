"""Verifica y procesa el webhook de confirmación de PayU.

La firma de confirmación es DISTINTA de la firma de envío que ya usa
`astro_frontend/src/pages/api/payu/prepare.ts` (esa es SHA256 sobre
`apiKey~merchantId~referenceCode~amount~currency`). La de confirmación es MD5 sobre:

    apiKey~merchant_id~reference_sale~new_value~currency~state_pol

Ver: https://developers.payulatam.com/latam/es/docs/integrations/confirmation-url.html
El monto llega en `value` (el webhook no trae `TX_VALUE`: ese es de la URL de respuesta)
y `new_value` es `value` con un solo decimal cuando el segundo es cero
(`150.00` → `150.0`, `150.25` → `150.25`). Se arma desde el string recibido, sin pasar
por `float`, para no cambiar un dígito.

El secreto `PAYU_API_KEY` vive sólo acá (Django), nunca se duplica en el runtime de
Astro: `confirmation.ts` es un proxy delgado que reenvía el payload crudo.
"""

import hashlib
import hmac
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from ..models import Pago, Pedido

# state_pol que manda PayU en el webhook de confirmación.
_ESTADO_POR_STATE_POL = {
    '4': 'aprobado',
    '6': 'rechazado',
    '5': 'rechazado',  # expirada: se trata como rechazada a nivel de negocio.
    '7': 'pendiente',
}


def valor_para_firma(value: str) -> str:
    """`new_value` de PayU: un decimal si el segundo es cero, si no dos."""
    entero, _, decimales = (value or '').strip().partition('.')
    decimales = (decimales + '00')[:2]
    return f"{entero}.{decimales[0]}" if decimales[1] == '0' else f"{entero}.{decimales}"


def verificar_firma(payload: dict) -> bool:
    api_key = settings.PAYU_API_KEY
    if not api_key:
        return False
    merchant_id = payload.get('merchant_id', '')
    referencia = payload.get('reference_sale', '')
    valor = valor_para_firma(payload.get('value', ''))
    moneda = payload.get('currency', '')
    estado = payload.get('state_pol', '')

    base = f"{api_key}~{merchant_id}~{referencia}~{valor}~{moneda}~{estado}"
    esperada = hashlib.md5(base.encode('utf-8')).hexdigest()
    recibida = (payload.get('sign') or '').lower()
    return hmac.compare_digest(esperada, recibida)


def _monto_coincide(payload: dict, pago: Pago) -> bool:
    try:
        return Decimal(str(payload.get('value', ''))) == pago.monto and payload.get('currency') == 'COP'
    except InvalidOperation:
        return False


@transaction.atomic
def procesar_confirmacion(payload: dict, firma_valida: bool) -> Pago | None:
    """Idempotente: reintentos de PayU con el mismo estado no repiten efectos.

    - Firma inválida: no toca ningún estado (si la referencia matchea un pago real,
      registra el intento en `raw_response`/`firma_valida` para auditoría).
    - `aprobado` es final: PayU documenta que, una vez aprobada una referencia, las
      notificaciones siguientes se pueden ignorar (p. ej. el rechazo de un intento
      anterior que llega tarde).
    - El comprador puede reintentar tras un rechazo con la misma referencia: si el
      reintento se aprueba, el pedido que el rechazo canceló vuelve a `pendiente`.
    - Un aprobado cuyo monto o moneda no coincide con el `Pago` no se aplica.
    """
    referencia = payload.get('reference_sale', '')
    try:
        pago = Pago.objects.select_for_update().select_related('id_pedido').get(referencia_payu=referencia)
    except Pago.DoesNotExist:
        return None

    if not firma_valida:
        pago.firma_valida = False
        pago.raw_response = payload
        pago.save(update_fields=['firma_valida', 'raw_response', 'updated_at'])
        return pago

    if pago.estado == 'aprobado' and pago.firma_valida:
        return pago

    nuevo_estado = _ESTADO_POR_STATE_POL.get(str(payload.get('state_pol', '')), 'pendiente')
    if nuevo_estado == 'aprobado' and not _monto_coincide(payload, pago):
        pago.raw_response = payload
        pago.save(update_fields=['raw_response', 'updated_at'])
        return pago

    if pago.estado == nuevo_estado and pago.firma_valida:
        # Mismo estado ya confirmado: reintento de PayU, no repetir efectos.
        return pago

    pago.estado = nuevo_estado
    pago.estado_payu = str(payload.get('state_pol', ''))
    pago.transaction_id = payload.get('transaction_id', '') or pago.transaction_id
    pago.order_id_payu = payload.get('reference_pol', '') or pago.order_id_payu
    pago.raw_response = payload
    pago.firma_valida = True
    pago.confirmado_en = timezone.now()
    pago.save()

    # El estado de Pago (cobro) y el de Pedido (logística) son cosas distintas: un pago
    # aprobado no adelanta el pedido a "enviado"/"entregado", eso lo decide el despacho.
    if nuevo_estado == 'rechazado':
        Pedido.objects.filter(pk=pago.id_pedido_id).update(estado='cancelado')
    elif nuevo_estado == 'aprobado':
        Pedido.objects.filter(pk=pago.id_pedido_id, estado='cancelado').update(estado='pendiente')

    return pago
