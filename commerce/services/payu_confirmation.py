"""Verifica y procesa el webhook de confirmación de PayU.

La firma de confirmación es DISTINTA de la firma de envío que ya usa
`astro_frontend/src/pages/api/payu/prepare.ts` (esa es SHA256 sobre
`apiKey~merchantId~referenceCode~amount~currency`). La de confirmación es MD5 sobre:

    apiKey~merchantId~referenceCode~TX_VALUE~currency~state_pol

Ver: https://developers.payulatam.com/latam/es/docs/integrations/webcheckout-integration/confirmation-page.html
`TX_VALUE` se usa tal cual llega (string literal) — igual criterio que `amount` en
`prepare.ts`: pasarlo por `Decimal`/`float` y volver a formatear puede cambiar un dígito
y romper la firma.

El secreto `PAYU_API_KEY` vive sólo acá (Django), nunca se duplica en el runtime de
Astro: `confirmation.ts` es un proxy delgado que reenvía el payload crudo.
"""

import hashlib

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


def verificar_firma(payload: dict) -> bool:
    api_key = settings.PAYU_API_KEY
    merchant_id = payload.get('merchant_id', '')
    referencia = payload.get('reference_sale', '')
    valor = payload.get('TX_VALUE', '')
    moneda = payload.get('currency', '')
    estado = payload.get('state_pol', '')

    base = f"{api_key}~{merchant_id}~{referencia}~{valor}~{moneda}~{estado}"
    esperada = hashlib.md5(base.encode('utf-8')).hexdigest()
    recibida = (payload.get('sign') or '').lower()
    return esperada.lower() == recibida


@transaction.atomic
def procesar_confirmacion(payload: dict, firma_valida: bool) -> Pago | None:
    """Idempotente: reintentos de PayU con el mismo estado no repiten efectos.

    Si la firma es inválida, no toca ningún estado (pero si la referencia matchea un
    pago real, registra el intento en `raw_response`/`firma_valida` para auditoría).
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

    nuevo_estado = _ESTADO_POR_STATE_POL.get(str(payload.get('state_pol', '')), 'pendiente')
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

    return pago
