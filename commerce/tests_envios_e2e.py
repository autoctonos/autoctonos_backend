"""Pedidos de punta a punta con el tarifario y la cobertura REALES del repo.

A diferencia de `DatosEnvioMixin` (una réplica a mano), aquí las tarifas y los trayectos
de cada municipio salen de `shipping/data/*.json` vía `seed_shipping`, igual que en
producción. Si alguien cambia el tarifario o la cobertura, estos montos lo delatan.

Cada caso recorre el camino completo que hace el checkout:
cotizar (`/api/envios/cotizar/`) → crear pedido (`/api/commerce/pedidos/crear/`) →
confirmación de PayU (`/api/commerce/pagos/confirmar/`), y comprueba que el monto que se
cotiza, el que queda en el Pedido/Envio y el que confirma PayU son el mismo.

Montos (COP), con el tarifario vigente:
    urbano 8.150 + 3.850/kg adicional · zonal 11.900 + 4.400 · nacional 18.200 + 4.800
    sobreflete = máx(800, 2 % del subtotal) · envío = flete + sobreflete
"""

import hashlib
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from locations.models import Departamento, Municipio
from producers.models import Productor
from products.models import Categoria, Producto
from shipping.models import PromocionEnvio

from .models import Envio, Pago, Pedido

COMPRADOR = {
    'nombre': 'Ana Pérez', 'email': 'ana@example.com', 'telefono': '3009998877',
    'tipo_documento': 'CC', 'documento': '123456789',
}
API_KEY = 'e2e-api-key'
MERCHANT_ID = '508029'


def firma_payu(referencia, valor, estado):
    base = f"{API_KEY}~{MERCHANT_ID}~{referencia}~{valor}~COP~{estado}"
    return hashlib.md5(base.encode('utf-8')).hexdigest()


@override_settings(PAYU_API_KEY=API_KEY)
class PedidosConTarifarioRealTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        boyaca = Departamento.objects.create(nombre='Boyacá')
        cundinamarca = Departamento.objects.create(nombre='Cundinamarca')
        antioquia = Departamento.objects.create(nombre='Antioquia')
        cls.tunja = Municipio.objects.create(id_departamento=boyaca, nombre='Tunja')
        cls.motavita = Municipio.objects.create(id_departamento=boyaca, nombre='Motavita')
        cls.duitama = Municipio.objects.create(id_departamento=boyaca, nombre='Duitama')
        cls.bogota = Municipio.objects.create(id_departamento=cundinamarca, nombre='Bogotá D.C.')
        cls.medellin = Municipio.objects.create(id_departamento=antioquia, nombre='Medellín')

        # Tarifas, cobertura, empaque y promoción tal como se siembran en producción.
        call_command('seed_shipping', '--allow-missing', stdout=StringIO(), stderr=StringIO())
        # La promoción de flete gratis se prueba aparte (está pausada en la tienda).
        PromocionEnvio.objects.update(activo=False)

        categoria = Categoria.objects.create(nombre='Lácteos', requiere_frio=False)

        def productor(nombre, municipio):
            return Productor.objects.create(nombre=nombre, descripcion=nombre,
                                            telefono='3001112233', id_municipio=municipio)

        def producto(nombre, dueño, precio, peso):
            return Producto.objects.create(
                id_categoria=categoria, nombre=nombre, descripcion=nombre,
                precio=Decimal(precio), stock=500, peso_kg=Decimal(peso),
                id_productor=dueño, estado='aprobado',
            )

        cls.almojabana = producto('Almojábana', productor('Panadería Tunja', cls.tunja), '10000', '0.500')
        cls.queso_motavita = producto('Queso Motavita', productor('Quesos Motavita', cls.motavita),
                                      '30000', '0.800')
        cls.queso_duitama = producto('Queso Duitama', productor('Lácteos Duitama', cls.duitama),
                                     '30000', '0.800')

    # ------------------------------------------------------------------ helpers

    def cotizar(self, destino, items):
        respuesta = self.client.post(reverse('envios-cotizar'), {
            'id_municipio_destino': destino.id_municipio,
            'items': [{'id_producto': p.id_producto, 'cantidad': c} for p, c in items],
        }, content_type='application/json')
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        return respuesta.json()

    def comprar(self, destino, items):
        """Cotiza, crea el pedido y lo aprueba por PayU. Devuelve (cotización, pedido)."""
        cotizacion = self.cotizar(destino, items)
        respuesta = self.client.post(reverse('pedidos-crear'), {
            'comprador': COMPRADOR,
            'id_municipio_destino': destino.id_municipio,
            'items': [{'id_producto': p.id_producto, 'cantidad': c} for p, c in items],
        }, content_type='application/json')
        self.assertEqual(respuesta.status_code, 201, respuesta.content)
        creado = respuesta.json()
        # Lo que firma prepare.ts para PayU es `totales.total` de la cotización, verbatim.
        self.assertEqual(creado['total'], cotizacion['totales']['total'])

        pago = Pago.objects.get(referencia_payu=creado['referencia_payu'])
        valor = str(pago.monto)
        self.assertEqual(valor, cotizacion['totales']['total'])
        confirmacion = self.client.post(reverse('pagos-confirmar'), {
            'merchant_id': MERCHANT_ID, 'reference_sale': pago.referencia_payu,
            'TX_VALUE': valor, 'currency': 'COP', 'state_pol': '4',
            'sign': firma_payu(pago.referencia_payu, valor, '4'),
        }, content_type='application/json')
        self.assertEqual(confirmacion.status_code, 200)
        pago.refresh_from_db()
        self.assertEqual(pago.estado, 'aprobado')
        return cotizacion, Pedido.objects.get(pk=creado['id_pedido'])

    def assertGuia(self, envio, *, trayecto, flete, sobreflete, dias):
        self.assertEqual(envio.trayecto_aplicado, trayecto)
        self.assertEqual(envio.flete, Decimal(flete))
        self.assertEqual(envio.sobreflete, Decimal(sobreflete))
        self.assertEqual((envio.entrega_dias_min, envio.entrega_dias_max), dias)

    def assertPedido(self, pedido, *, subtotal, envio, total, dias):
        self.assertEqual(pedido.subtotal_productos, Decimal(subtotal))
        self.assertEqual(pedido.envio, Decimal(envio))
        self.assertEqual(pedido.total, Decimal(total))
        self.assertEqual(pedido.descuento_envio, Decimal('0'))
        self.assertEqual((pedido.entrega_dias_min, pedido.entrega_dias_max), dias)

    # ---------------------------------------------------------- mismo municipio

    def test_tunja_a_tunja(self):
        """2 almojábanas (1 kg, $20.000): urbano 8.150 + sobreflete mínimo 800."""
        cotizacion, pedido = self.comprar(self.tunja, [(self.almojabana, 2)])
        self.assertEqual(cotizacion['grupos'][0]['valor_envio'], '8950.00')
        self.assertPedido(pedido, subtotal='20000', envio='8950', total='28950', dias=(1, 1))
        self.assertGuia(pedido.envios.get(), trayecto='urbano', flete='8150',
                        sobreflete='800', dias=(1, 1))

    def test_motavita_a_motavita_cobra_urbano_no_zonal(self):
        """5 quesos (4 kg, $150.000): 8.150 + 3 × 3.850 = 19.700 + 3.000 de sobreflete."""
        _, pedido = self.comprar(self.motavita, [(self.queso_motavita, 5)])
        self.assertPedido(pedido, subtotal='150000', envio='22700', total='172700', dias=(1, 1))
        self.assertGuia(pedido.envios.get(), trayecto='urbano', flete='19700',
                        sobreflete='3000', dias=(1, 1))

    def test_duitama_a_duitama(self):
        _, pedido = self.comprar(self.duitama, [(self.queso_duitama, 5)])
        self.assertPedido(pedido, subtotal='150000', envio='22700', total='172700', dias=(1, 1))

    # ------------------------------------------------------- municipios distintos

    def test_duitama_a_bogota_es_zonal(self):
        """5 quesos (4 kg): 11.900 + 3 × 4.400 = 25.100 + 3.000 de sobreflete."""
        _, pedido = self.comprar(self.bogota, [(self.queso_duitama, 5)])
        self.assertPedido(pedido, subtotal='150000', envio='28100', total='178100', dias=(1, 3))
        self.assertGuia(pedido.envios.get(), trayecto='zonal', flete='25100',
                        sobreflete='3000', dias=(1, 3))

    def test_duitama_a_medellin_es_nacional(self):
        """5 quesos (4 kg): 18.200 + 3 × 4.800 = 32.600 + 3.000 de sobreflete."""
        _, pedido = self.comprar(self.medellin, [(self.queso_duitama, 5)])
        self.assertPedido(pedido, subtotal='150000', envio='35600', total='185600', dias=(1, 4))
        self.assertGuia(pedido.envios.get(), trayecto='nacional', flete='32600',
                        sobreflete='3000', dias=(1, 4))

    def test_tunja_a_duitama_es_zonal(self):
        """Origen urbano no abarata un envío que sí sale del municipio: gana el zonal."""
        _, pedido = self.comprar(self.duitama, [(self.almojabana, 2)])
        self.assertPedido(pedido, subtotal='20000', envio='12700', total='32700', dias=(1, 3))

    def test_motavita_a_tunja_sigue_zonal(self):
        """El mismo queso que en Motavita cuesta 22.700 de envío, a 6,6 km cuesta 28.100."""
        _, pedido = self.comprar(self.tunja, [(self.queso_motavita, 5)])
        self.assertPedido(pedido, subtotal='150000', envio='28100', total='178100', dias=(1, 3))

    # ---------------------------------------------------------------- mezclas

    def test_carrito_mixto_en_tunja(self):
        """Almojábanas de Tunja (urbano, 8.950) + quesos de Duitama (zonal, 28.100).
        Dos guías; el pedido llega cuando llega la más lenta (1-3 días)."""
        cotizacion, pedido = self.comprar(self.tunja, [(self.almojabana, 2), (self.queso_duitama, 5)])
        self.assertEqual(len(cotizacion['grupos']), 2)
        self.assertPedido(pedido, subtotal='170000', envio='37050', total='207050', dias=(1, 3))
        guias = {e.id_municipio_origen_id: e for e in pedido.envios.all()}
        self.assertGuia(guias[self.tunja.id_municipio], trayecto='urbano', flete='8150',
                        sobreflete='800', dias=(1, 1))
        self.assertGuia(guias[self.duitama.id_municipio], trayecto='zonal', flete='25100',
                        sobreflete='3000', dias=(1, 3))

    def test_cotizacion_y_pedido_coinciden_guia_por_guia(self):
        """Lo que se muestra en el checkout es lo que queda grabado para despacho."""
        cotizacion, pedido = self.comprar(self.tunja, [(self.almojabana, 2), (self.queso_duitama, 5)])
        guardadas = {(e.id_municipio_origen_id, e.trayecto_aplicado, str(e.flete), str(e.sobreflete))
                     for e in Envio.objects.filter(id_pedido=pedido)}
        cotizadas = {(g['id_municipio_origen'], g['trayecto_aplicado'], g['flete'], g['sobreflete'])
                     for g in cotizacion['grupos']}
        self.assertEqual(guardadas, cotizadas)

    # --------------------------------------------------------------- promoción

    def test_promocion_activa_cubre_el_flete_sobre_200_mil(self):
        """La fila que siembra `seed_shipping` (umbral $200.000) sigue aplicando en el
        backend aunque la tienda ya no la anuncie. 7 quesos = 6 kg, $210.000."""
        PromocionEnvio.objects.update(activo=True)
        cerca, pedido_cerca = self.comprar(self.duitama, [(self.queso_duitama, 7)])
        lejos, pedido_lejos = self.comprar(self.bogota, [(self.queso_duitama, 7)])
        # Urbano 8.150 + 5 × 3.850 = 27.400 y zonal 11.900 + 5 × 4.400 = 33.900: ambos cubiertos.
        self.assertEqual(cerca['totales']['descuento_envio'], '27400.00')
        self.assertEqual(lejos['totales']['descuento_envio'], '33900.00')
        # Sólo se cobra el sobreflete (2 % de 210.000).
        self.assertEqual(pedido_cerca.envio, Decimal('4200'))
        self.assertEqual(pedido_lejos.envio, Decimal('4200'))
        self.assertEqual(pedido_cerca.total, Decimal('214200'))
