import hashlib
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from shipping.services.quote import cotizar
from shipping.services.repository import construir_entrada
from shipping.tests import DatosEnvioMixin

from .models import DetallePedido, Envio, Pago, Pedido
from .services.order_creation import crear_pedido_pendiente
from .services.payu_confirmation import procesar_confirmacion, verificar_firma

COMPRADOR = {
    'nombre': 'Ana Pérez', 'email': 'ana@example.com', 'telefono': '3009998877',
    'tipo_documento': 'CC', 'documento': '123456789',
}


def firmar(api_key, merchant_id, referencia, valor, moneda, estado):
    base = f"{api_key}~{merchant_id}~{referencia}~{valor}~{moneda}~{estado}"
    return hashlib.md5(base.encode('utf-8')).hexdigest()


class CrearPedidoServiceTests(DatosEnvioMixin, TestCase):
    """`crear_pedido_pendiente` debe persistir exactamente lo que `quote.cotizar` calcula:
    reusa `shipping.services.repository`/`quote` en vez de recalcular nada distinto."""

    def setUp(self):
        self.crear_datos()

    def test_crea_un_envio_por_grupo_y_totales_coinciden_con_la_cotizacion(self):
        datos = {
            'comprador': COMPRADOR,
            'id_municipio_destino': self.tunja.id_municipio,
            'items': [
                {'id_producto': self.queso.id_producto, 'cantidad': 5},
                {'id_producto': self.sabajon.id_producto, 'cantidad': 1},
            ],
        }
        pedido, pago = crear_pedido_pendiente(datos)

        entrada = construir_entrada(datos['id_municipio_destino'], datos['items'])
        esperado = cotizar(entrada)

        self.assertEqual(Pedido.objects.count(), 1)
        # Dos productores distintos (productor_a: queso, productor_b: sabajón) => 2 Envio.
        self.assertEqual(Envio.objects.filter(id_pedido=pedido).count(), 2)
        self.assertEqual(DetallePedido.objects.filter(id_pedido=pedido).count(), 2)

        self.assertEqual(pedido.total, esperado.totales.total)
        self.assertEqual(pedido.subtotal_productos, esperado.totales.subtotal_productos)
        self.assertEqual(pedido.flete, esperado.totales.flete)
        self.assertEqual(pedido.comprador_nombre, COMPRADOR['nombre'])
        self.assertEqual(pedido.estado, 'pendiente')

        self.assertEqual(pago.estado, 'pendiente')
        self.assertTrue(pago.referencia_payu.startswith('PEDIDO-'))
        # No debe ser el PK secuencial: exponerlo filtraría el volumen de ventas.
        self.assertNotEqual(pago.referencia_payu, f"PEDIDO-{pedido.id_pedido}")
        self.assertEqual(pago.monto, esperado.totales.total)

    def test_producto_no_cotizable_hace_rollback_completo(self):
        sin_peso = self.queso
        sin_peso.peso_kg = None
        sin_peso.save(update_fields=['peso_kg'])

        datos = {
            'comprador': COMPRADOR,
            'id_municipio_destino': self.tunja.id_municipio,
            'items': [{'id_producto': sin_peso.id_producto, 'cantidad': 1}],
        }
        with self.assertRaises(Exception):
            crear_pedido_pendiente(datos)

        self.assertEqual(Pedido.objects.count(), 0)
        self.assertEqual(Envio.objects.count(), 0)
        self.assertEqual(Pago.objects.count(), 0)

    def test_referencia_payu_opaca_y_unica(self):
        datos = {
            'comprador': COMPRADOR,
            'id_municipio_destino': self.tunja.id_municipio,
            'items': [{'id_producto': self.queso.id_producto, 'cantidad': 1}],
        }
        _, pago_1 = crear_pedido_pendiente(datos)
        _, pago_2 = crear_pedido_pendiente(datos)
        self.assertNotEqual(pago_1.referencia_payu, pago_2.referencia_payu)
        self.assertTrue(pago_1.referencia_payu.startswith('PEDIDO-'))

    def test_guest_sin_usuario(self):
        datos = {
            'comprador': COMPRADOR,
            'id_municipio_destino': self.tunja.id_municipio,
            'items': [{'id_producto': self.queso.id_producto, 'cantidad': 1}],
        }
        pedido, _ = crear_pedido_pendiente(datos)
        self.assertIsNone(pedido.id_usuario)


class CrearPedidoAPITests(DatosEnvioMixin, TestCase):

    def setUp(self):
        self.crear_datos()
        self.url = reverse('pedidos-crear')

    def test_crear_pedido_end_to_end(self):
        respuesta = self.client.post(self.url, {
            'comprador': COMPRADOR,
            'id_municipio_destino': self.tunja.id_municipio,
            'items': [{'id_producto': self.queso.id_producto, 'cantidad': 5}],
        }, content_type='application/json')
        self.assertEqual(respuesta.status_code, 201)
        cuerpo = respuesta.json()
        self.assertEqual(cuerpo['total'], '178100.00')
        self.assertTrue(cuerpo['referencia_payu'].startswith('PEDIDO-'))

    def test_destino_no_soportado_devuelve_422(self):
        respuesta = self.client.post(self.url, {
            'comprador': COMPRADOR,
            'id_municipio_destino': 999999,
            'items': [{'id_producto': self.queso.id_producto, 'cantidad': 1}],
        }, content_type='application/json')
        self.assertEqual(respuesta.status_code, 422)
        self.assertEqual(respuesta.json()['code'], 'destino_no_soportado')


class ConfirmacionPayUTests(DatosEnvioMixin, TestCase):

    def setUp(self):
        self.crear_datos()
        pedido, self.pago = crear_pedido_pendiente({
            'comprador': COMPRADOR,
            'id_municipio_destino': self.tunja.id_municipio,
            'items': [{'id_producto': self.queso.id_producto, 'cantidad': 1}],
        })
        self.pedido = pedido
        self.api_key = 'test-api-key'
        self.merchant_id = '999888'
        from django.test import override_settings
        self._override = override_settings(PAYU_API_KEY=self.api_key)
        self._override.enable()
        self.addCleanup(self._override.disable)

    def _payload(self, estado='4', valor=None, sign=None):
        valor = valor if valor is not None else str(self.pago.monto)
        payload = {
            'merchant_id': self.merchant_id,
            'reference_sale': self.pago.referencia_payu,
            'TX_VALUE': valor,
            'currency': 'COP',
            'state_pol': estado,
            'transaction_id': 'tx-1',
            'reference_pol': 'pol-1',
        }
        payload['sign'] = sign if sign is not None else firmar(
            self.api_key, self.merchant_id, payload['reference_sale'], valor, 'COP', estado)
        return payload

    def test_firma_valida_aprobado_actualiza_pago(self):
        payload = self._payload(estado='4')
        firma_valida = verificar_firma(payload)
        self.assertTrue(firma_valida)

        procesar_confirmacion(payload, firma_valida)
        self.pago.refresh_from_db()
        self.assertEqual(self.pago.estado, 'aprobado')
        self.assertTrue(self.pago.firma_valida)
        self.assertIsNotNone(self.pago.confirmado_en)

    def test_firma_invalida_no_actualiza_nada(self):
        payload = self._payload(estado='4', sign='firma-corrupta')
        firma_valida = verificar_firma(payload)
        self.assertFalse(firma_valida)

        procesar_confirmacion(payload, firma_valida)
        self.pago.refresh_from_db()
        self.assertEqual(self.pago.estado, 'pendiente')

    def test_webhook_repetido_es_idempotente(self):
        payload = self._payload(estado='4')
        firma_valida = verificar_firma(payload)
        procesar_confirmacion(payload, firma_valida)
        primera_confirmacion = self.pago.confirmado_en = Pago.objects.get(pk=self.pago.pk).confirmado_en

        procesar_confirmacion(payload, firma_valida)
        self.pago.refresh_from_db()
        # Mismo estado ya confirmado: no debe volver a tocar confirmado_en.
        self.assertEqual(self.pago.confirmado_en, primera_confirmacion)

    def test_rechazado_cancela_el_pedido(self):
        payload = self._payload(estado='6')
        firma_valida = verificar_firma(payload)
        procesar_confirmacion(payload, firma_valida)
        self.pago.refresh_from_db()
        self.pedido.refresh_from_db()
        self.assertEqual(self.pago.estado, 'rechazado')
        self.assertEqual(self.pedido.estado, 'cancelado')

    def test_referencia_inexistente_no_falla(self):
        payload = self._payload(estado='4')
        payload['reference_sale'] = 'PEDIDO-999999'
        payload['sign'] = firmar(self.api_key, self.merchant_id, payload['reference_sale'],
                                 payload['TX_VALUE'], 'COP', '4')
        firma_valida = verificar_firma(payload)
        resultado = procesar_confirmacion(payload, firma_valida)
        self.assertIsNone(resultado)


class ConfirmacionPayUAPITests(DatosEnvioMixin, TestCase):

    def setUp(self):
        self.crear_datos()
        _, self.pago = crear_pedido_pendiente({
            'comprador': COMPRADOR,
            'id_municipio_destino': self.tunja.id_municipio,
            'items': [{'id_producto': self.queso.id_producto, 'cantidad': 1}],
        })
        self.url = reverse('pagos-confirmar')
        from django.test import override_settings
        self._override = override_settings(PAYU_API_KEY='test-api-key')
        self._override.enable()
        self.addCleanup(self._override.disable)

    def test_confirmar_pago_end_to_end(self):
        valor = str(self.pago.monto)
        payload = {
            'merchant_id': '999888',
            'reference_sale': self.pago.referencia_payu,
            'TX_VALUE': valor,
            'currency': 'COP',
            'state_pol': '4',
            'sign': firmar('test-api-key', '999888', self.pago.referencia_payu, valor, 'COP', '4'),
        }
        respuesta = self.client.post(self.url, payload, content_type='application/json')
        self.assertEqual(respuesta.status_code, 200)
        self.pago.refresh_from_db()
        self.assertEqual(self.pago.estado, 'aprobado')
