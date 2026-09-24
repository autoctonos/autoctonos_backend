import json
import tempfile
from dataclasses import replace
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from locations.models import Departamento, Municipio
from producers.models import Productor
from products.models import Categoria, Producto

from .models import CoberturaMunicipio, ConfiguracionEmpaque, PromocionEnvio, Trayecto
from .services.quote import (
    ConfigEmpaque,
    Destino,
    EntradaCotizacion,
    EntregaEstimada,
    ItemCotizacion,
    ParametrosCalculo,
    PromocionCalculo,
    TarifaTrayecto,
    cotizar,
    kilos_adicionales,
)

# Tarifas y días tal como están en la hoja «Convenciones» del tarifario.
URBANO = TarifaTrayecto('urbano', 'Urbano', 1, Decimal('8150'), Decimal('3850'),
                        Decimal('800'), Decimal('0.0200'), 1, 1)
ZONAL = TarifaTrayecto('zonal', 'Zonal', 2, Decimal('11900'), Decimal('4400'),
                       Decimal('800'), Decimal('0.0200'), 1, 3)
NACIONAL = TarifaTrayecto('nacional', 'Nacional', 3, Decimal('18200'), Decimal('4800'),
                          Decimal('800'), Decimal('0.0200'), 1, 4)
TERRITORIAL = TarifaTrayecto('territorial', 'Territorial', 4, Decimal('19800'), Decimal('4850'),
                             Decimal('800'), Decimal('0.0200'), 1, 4)
ESPECIAL = TarifaTrayecto('especial', 'Especial', 5, Decimal('38400'), Decimal('12450'),
                          Decimal('800'), Decimal('0.0200'), 8, 10)
EMPAQUE = ConfigEmpaque(capacidad_kg=Decimal('6.000'), costo_nevera=Decimal('12000.00'))

TUNJA = Destino(id_municipio=1104, nombre='Tunja', departamento='Boyacá', tarifa=URBANO)


def item(**kwargs):
    base = dict(
        id_producto=42, nombre='Queso Paipa', cantidad=1,
        precio_unitario=Decimal('30000'), peso_unitario_kg=Decimal('0.800'),
        requiere_frio=False, id_productor=7, productor='Lácteos El Roble',
        id_municipio_origen=1069, municipio_origen='Paipa',
        departamento_origen='Boyacá', tarifa_origen=ZONAL,
    )
    base.update(kwargs)
    return ItemCotizacion(**base)


def escribir_cobertura(filas):
    archivo = tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf-8')
    json.dump(filas, archivo, ensure_ascii=False)
    archivo.close()
    return archivo.name


def entrada(items, destino=TUNJA, parametros=None):
    return EntradaCotizacion(
        destino=destino,
        items=tuple(items),
        config_empaque=EMPAQUE,
        parametros=parametros or ParametrosCalculo(),
    )


class CalculoFleteTests(SimpleTestCase):

    def test_caso_queso_paipa(self):
        """El ejemplo verificado del tarifario: 5 quesos de Paipa a Tunja."""
        resultado = cotizar(entrada([item(cantidad=5)]))
        grupo = resultado.grupos[0]

        self.assertEqual(grupo.peso_bruto_kg, Decimal('4.000'))
        self.assertEqual(grupo.peso_facturable_kg, 4)
        self.assertEqual(grupo.kilos_adicionales, 3)
        self.assertEqual(grupo.trayecto_aplicado, 'zonal')
        self.assertEqual(grupo.jerarquia, 2)
        self.assertEqual(grupo.subtotal, Decimal('150000.00'))
        self.assertEqual(grupo.flete, Decimal('25100.00'))
        self.assertEqual(grupo.sobreflete, Decimal('3000.00'))
        self.assertEqual(grupo.empaque, Decimal('0.00'))
        self.assertEqual(grupo.total_grupo, Decimal('178100.00'))
        self.assertEqual(resultado.totales.envio, Decimal('28100.00'))
        self.assertEqual(resultado.totales.total, Decimal('178100.00'))

    def test_peso_exactamente_1kg_no_paga_adicional(self):
        """`SI(peso>=1; peso-1; peso)` del tarifario vigente."""
        self.assertEqual(kilos_adicionales(1), 0)
        resultado = cotizar(entrada([item(peso_unitario_kg=Decimal('1.000'))]))
        self.assertEqual(resultado.grupos[0].kilos_adicionales, 0)
        self.assertEqual(resultado.grupos[0].flete, Decimal('11900.00'))

    def test_peso_fraccionario_redondea_arriba(self):
        resultado = cotizar(entrada([item(cantidad=3, peso_unitario_kg=Decimal('0.400'))]))
        grupo = resultado.grupos[0]
        self.assertEqual(grupo.peso_bruto_kg, Decimal('1.200'))
        self.assertEqual(grupo.peso_facturable_kg, 2)
        self.assertEqual(grupo.kilos_adicionales, 1)

    def test_sobreflete_cae_en_minimo(self):
        resultado = cotizar(entrada([item(precio_unitario=Decimal('20000'))]))
        self.assertEqual(resultado.grupos[0].sobreflete, Decimal('800.00'))

    def test_sobreflete_en_el_borde(self):
        resultado = cotizar(entrada([item(precio_unitario=Decimal('40000'))]))
        self.assertEqual(resultado.grupos[0].sobreflete, Decimal('800.00'))

    def test_jerarquia_toma_el_maximo(self):
        # Origen zonal (2) + destino urbano (1) => zonal.
        resultado = cotizar(entrada([item()]))
        self.assertEqual(resultado.grupos[0].trayecto_aplicado, 'zonal')

        # Origen urbano (1) + destino nacional (3) => nacional.
        destino_lejano = Destino(1, 'Cali', 'Valle del Cauca', NACIONAL)
        resultado = cotizar(entrada([item(tarifa_origen=URBANO)], destino=destino_lejano))
        self.assertEqual(resultado.grupos[0].trayecto_aplicado, 'nacional')
        self.assertEqual(resultado.grupos[0].jerarquia, 3)

    def test_carrito_multi_productor(self):
        """Dos productores son dos guías: dos fletes y dos sobrefletes."""
        resultado = cotizar(entrada([
            item(id_producto=1, id_productor=1, productor='A',
                 id_municipio_origen=1069, municipio_origen='Paipa',
                 precio_unitario=Decimal('10000')),
            item(id_producto=2, id_productor=2, productor='B',
                 id_municipio_origen=1080, municipio_origen='Sogamoso',
                 precio_unitario=Decimal('10000')),
        ]))
        self.assertEqual(len(resultado.grupos), 2)
        self.assertEqual(resultado.totales.sobreflete, Decimal('1600.00'))
        self.assertEqual(resultado.totales.flete, Decimal('23800.00'))

    def test_un_productor_varios_productos_es_un_solo_flete(self):
        """Todo lo del mismo productor viaja junto: peso y subtotal se suman."""
        resultado = cotizar(entrada([
            item(id_producto=1, cantidad=2, peso_unitario_kg=Decimal('1.000'),
                 precio_unitario=Decimal('50000')),
            item(id_producto=2, cantidad=1, peso_unitario_kg=Decimal('2.000'),
                 precio_unitario=Decimal('50000')),
        ]))
        self.assertEqual(len(resultado.grupos), 1)
        grupo = resultado.grupos[0]
        self.assertEqual(grupo.peso_bruto_kg, Decimal('4.000'))
        self.assertEqual(grupo.subtotal, Decimal('150000.00'))
        self.assertEqual(grupo.flete, Decimal('25100.00'))
        self.assertEqual(grupo.sobreflete, Decimal('3000.00'))

    def test_dos_productores_mismo_municipio_son_dos_fletes(self):
        """La regla nueva: el cobro es por productor, no por bodega geográfica."""
        resultado = cotizar(entrada([
            item(id_producto=1, id_productor=1, productor='A'),
            item(id_producto=2, id_productor=2, productor='B'),
        ]))
        self.assertEqual(len(resultado.grupos), 2)
        self.assertEqual({g.id_municipio_origen for g in resultado.grupos}, {1069})
        self.assertEqual(resultado.totales.flete, Decimal('23800.00'))

    def test_mismo_productor_dos_municipios_son_dos_fletes(self):
        """Justifica la clave compuesta: son dos recogidas y tarifan distinto."""
        resultado = cotizar(entrada([
            item(id_producto=1, id_municipio_origen=1069, municipio_origen='Paipa'),
            item(id_producto=2, id_municipio_origen=1080, municipio_origen='Sogamoso',
                 tarifa_origen=URBANO),
        ]))
        self.assertEqual(len(resultado.grupos), 2)

    def test_orden_de_grupos_es_determinista(self):
        """El mismo carrito en distinto orden produce la misma cotización."""
        items = [
            item(id_producto=1, id_productor=3, productor='Zulia'),
            item(id_producto=2, id_productor=1, productor='Andes'),
            item(id_producto=3, id_productor=2, productor='medina'),
        ]
        orden_a = [g.productor for g in cotizar(entrada(items)).grupos]
        orden_b = [g.productor for g in cotizar(entrada(list(reversed(items)))).grupos]
        self.assertEqual(orden_a, ['Andes', 'medina', 'Zulia'])
        self.assertEqual(orden_a, orden_b)

    def test_empaque_por_grupo(self):
        """Cada productor empaca lo suyo: no comparten nevera."""
        resultado = cotizar(entrada([
            item(id_producto=1, id_productor=1, productor='A', cantidad=4,
                 peso_unitario_kg=Decimal('1.000'), requiere_frio=True),
            item(id_producto=2, id_productor=2, productor='B',
                 id_municipio_origen=1080, municipio_origen='Sogamoso',
                 cantidad=4, peso_unitario_kg=Decimal('1.000'), requiere_frio=True),
        ]))
        self.assertEqual([g.neveras for g in resultado.grupos], [1, 1])
        self.assertEqual(resultado.totales.empaque, Decimal('24000.00'))

        # 3 kg + 3 kg: agrupar globalmente daría 1 nevera y sub-cobraría.
        resultado = cotizar(entrada([
            item(id_producto=1, id_productor=1, productor='A', cantidad=3,
                 peso_unitario_kg=Decimal('1.000'), requiere_frio=True),
            item(id_producto=2, id_productor=2, productor='B',
                 id_municipio_origen=1080, municipio_origen='Sogamoso',
                 cantidad=3, peso_unitario_kg=Decimal('1.000'), requiere_frio=True),
        ]))
        self.assertEqual([g.neveras for g in resultado.grupos], [1, 1])
        self.assertEqual(resultado.totales.empaque, Decimal('24000.00'))

    def test_requiere_frio_override_gana_sobre_categoria(self):
        """El override viaja resuelto hasta el cálculo; aquí se pinea el efecto."""
        frio = cotizar(entrada([item(requiere_frio=True)]))
        sin_frio = cotizar(entrada([item(requiere_frio=False)]))
        self.assertEqual(frio.grupos[0].neveras, 1)
        self.assertEqual(frio.grupos[0].empaque, Decimal('12000.00'))
        self.assertEqual(sin_frio.grupos[0].neveras, 0)
        self.assertEqual(sin_frio.grupos[0].empaque, Decimal('0.00'))

    def test_promocion_solo_cubre_el_flete(self):
        """El sobreflete es la garantía del producto: nunca entra al descuento."""
        promocion = PromocionCalculo(umbral_subtotal=Decimal('200000.00'))
        resultado = cotizar(entrada(
            [item(cantidad=10, requiere_frio=True)],
            parametros=ParametrosCalculo(promocion=promocion),
        ))
        grupo = resultado.grupos[0]
        self.assertTrue(resultado.promocion.aplicada)
        self.assertEqual(resultado.promocion.descuento, grupo.flete)
        self.assertGreater(grupo.empaque, Decimal('0'))
        self.assertEqual(resultado.totales.envio, grupo.sobreflete + grupo.empaque)

    def test_promocion_nunca_deja_el_envio_en_cero(self):
        """Con el sobreflete siempre cobrado, «envío gratis» ya no existe."""
        promocion = PromocionCalculo(umbral_subtotal=Decimal('200000.00'))
        resultado = cotizar(entrada(
            [item(cantidad=10)],
            parametros=ParametrosCalculo(promocion=promocion),
        ))
        self.assertTrue(resultado.promocion.aplicada)
        self.assertEqual(resultado.totales.envio, resultado.totales.sobreflete)
        self.assertGreaterEqual(resultado.totales.envio, Decimal('800.00'))

    def test_entrega_con_un_solo_grupo_es_la_del_trayecto(self):
        # Origen zonal (1-3) + destino urbano (1-1) => aplica zonal.
        resultado = cotizar(entrada([item()]))
        self.assertEqual(resultado.grupos[0].entrega, EntregaEstimada(1, 3))
        self.assertEqual(resultado.entrega, EntregaEstimada(1, 3))

    def test_dias_salen_del_trayecto_aplicado(self):
        """Igual que el flete: manda `MAX(jerarquía origen, destino)`."""
        destino_lejano = Destino(1, 'Leticia', 'Amazonas', ESPECIAL)
        resultado = cotizar(entrada([item()], destino=destino_lejano))
        self.assertEqual(resultado.grupos[0].trayecto_aplicado, 'especial')
        self.assertEqual(resultado.grupos[0].entrega, EntregaEstimada(8, 10))

    def test_entrega_global_toma_el_grupo_mas_lento(self):
        """El pedido está completo cuando llega el último paquete: 1-1 + 8-10 => 8-10."""
        resultado = cotizar(entrada([
            item(id_producto=1, id_productor=1, productor='A', tarifa_origen=URBANO),
            item(id_producto=2, id_productor=2, productor='B', tarifa_origen=ESPECIAL),
        ]))
        self.assertEqual([g.entrega for g in resultado.grupos],
                         [EntregaEstimada(1, 1), EntregaEstimada(8, 10)])
        # No es 1-10: es imposible tener todo el pedido en un día.
        self.assertEqual(resultado.entrega, EntregaEstimada(8, 10))

    def test_promocion_no_aplica_bajo_el_umbral(self):
        promocion = PromocionCalculo(umbral_subtotal=Decimal('200000.00'))
        resultado = cotizar(entrada([item(cantidad=5)],
                                    parametros=ParametrosCalculo(promocion=promocion)))
        self.assertFalse(resultado.promocion.aplicada)
        self.assertEqual(resultado.promocion.descuento, Decimal('0'))
        self.assertEqual(resultado.totales.total, Decimal('178100.00'))

    def test_todo_es_decimal(self):
        resultado = cotizar(entrada([item(cantidad=5, requiere_frio=True)]))
        monetarios = [
            resultado.totales.subtotal_productos, resultado.totales.flete,
            resultado.totales.sobreflete, resultado.totales.empaque,
            resultado.totales.descuento_envio, resultado.totales.envio,
            resultado.totales.total, resultado.promocion.descuento,
        ]
        grupo = resultado.grupos[0]
        monetarios += [grupo.subtotal, grupo.flete, grupo.sobreflete, grupo.empaque,
                       grupo.total_grupo, grupo.valor_kilo_inicial, grupo.valor_kilo_adicional,
                       grupo.peso_bruto_kg, grupo.peso_frio_kg]
        monetarios += [linea.precio_unitario for linea in grupo.items]
        monetarios += [linea.subtotal for linea in grupo.items]
        for valor in monetarios:
            self.assertIsInstance(valor, Decimal)
        self.assertIsInstance(grupo.peso_facturable_kg, int)
        self.assertIsInstance(grupo.neveras, int)


class DatosEnvioMixin:
    """Réplica mínima del tarifario y la cobertura, sin correr el seeder."""

    def crear_datos(self):
        self.urbano = Trayecto.objects.create(
            codigo='urbano', nombre='Urbano', jerarquia=1,
            valor_kilo_inicial=Decimal('8150'), valor_kilo_adicional=Decimal('3850'),
            dias_entrega_min=1, dias_entrega_max=1,
        )
        self.zonal = Trayecto.objects.create(
            codigo='zonal', nombre='Zonal', jerarquia=2,
            valor_kilo_inicial=Decimal('11900'), valor_kilo_adicional=Decimal('4400'),
            dias_entrega_min=1, dias_entrega_max=3,
        )
        self.nacional = Trayecto.objects.create(
            codigo='nacional', nombre='Nacional', jerarquia=3,
            valor_kilo_inicial=Decimal('18200'), valor_kilo_adicional=Decimal('4800'),
            dias_entrega_min=1, dias_entrega_max=4,
        )

        self.territorial = Trayecto.objects.create(
            codigo='territorial', nombre='Territorial', jerarquia=4,
            valor_kilo_inicial=Decimal('19800'), valor_kilo_adicional=Decimal('4850'),
            dias_entrega_min=1, dias_entrega_max=4,
        )

        self.boyaca = Departamento.objects.create(nombre='Boyacá')
        self.amazonas = Departamento.objects.create(nombre='Amazonas')
        self.casanare = Departamento.objects.create(nombre='Casanare')
        self.tunja = Municipio.objects.create(id_departamento=self.boyaca, nombre='Tunja')
        self.paipa = Municipio.objects.create(id_departamento=self.boyaca, nombre='Paipa')
        self.sogamoso = Municipio.objects.create(id_departamento=self.boyaca, nombre='Sogamoso')
        self.pajarito = Municipio.objects.create(id_departamento=self.boyaca, nombre='Pajarito')
        self.leticia = Municipio.objects.create(id_departamento=self.amazonas, nombre='Leticia')
        self.yopal = Municipio.objects.create(id_departamento=self.casanare, nombre='Yopal')

        CoberturaMunicipio.objects.create(
            municipio=self.tunja, trayecto_origen=self.urbano, trayecto_destino=self.urbano)
        CoberturaMunicipio.objects.create(
            municipio=self.paipa, trayecto_origen=self.zonal, trayecto_destino=self.zonal)
        CoberturaMunicipio.objects.create(
            municipio=self.sogamoso, trayecto_origen=None, trayecto_destino=self.zonal)
        CoberturaMunicipio.objects.create(
            municipio=self.pajarito, trayecto_origen=self.territorial,
            trayecto_destino=self.territorial)
        CoberturaMunicipio.objects.create(
            municipio=self.yopal, trayecto_origen=None, trayecto_destino=self.nacional)

        self.productor_a = Productor.objects.create(
            nombre='Lácteos El Roble', descripcion='Quesos', telefono='3001112233',
            id_municipio=self.paipa,
        )
        self.productor_b = Productor.objects.create(
            nombre='Sabajón del Llano', descripcion='Licores', telefono='3004445566',
            id_municipio=self.pajarito,
        )

        ConfiguracionEmpaque.objects.create(
            capacidad_kg=Decimal('6.000'), costo_nevera=Decimal('12000.00'))
        PromocionEnvio.objects.create(
            umbral_subtotal=Decimal('200000.00'), cubre_empaque=False)

        # `requiere_frio=False` a propósito: si se cambia, los golden suman una nevera de
        # $12.000 y dejan de cuadrar sin que se entienda por qué.
        self.categoria = Categoria.objects.create(nombre='Lácteos', requiere_frio=False)
        self.queso = Producto.objects.create(
            id_categoria=self.categoria, nombre='Queso Paipa', descripcion='Queso',
            precio=Decimal('30000.00'), stock=100, peso_kg=Decimal('0.800'),
            id_productor=self.productor_a, estado='aprobado',
        )
        self.sabajon = Producto.objects.create(
            id_categoria=self.categoria, nombre='Sabajón', descripcion='Sabajón',
            precio=Decimal('85000.00'), stock=100, peso_kg=Decimal('1.200'),
            id_productor=self.productor_b, estado='aprobado',
        )


class CotizacionAPITests(DatosEnvioMixin, TestCase):

    def setUp(self):
        self.crear_datos()
        self.url = reverse('envios-cotizar')

    def cotizar(self, payload):
        return self.client.post(self.url, payload, content_type='application/json')

    def test_cotiza_caso_paipa_end_to_end(self):
        respuesta = self.cotizar({
            'id_municipio_destino': self.tunja.id_municipio,
            'items': [{'id_producto': self.queso.id_producto, 'cantidad': 5}],
        })
        self.assertEqual(respuesta.status_code, 200)
        cuerpo = respuesta.json()
        self.assertEqual(cuerpo['totales']['total'], '178100.00')
        self.assertEqual(cuerpo['totales']['flete'], '25100.00')
        self.assertEqual(cuerpo['totales']['sobreflete'], '3000.00')
        self.assertEqual(cuerpo['totales']['envio'], '28100.00')
        self.assertEqual(cuerpo['moneda'], 'COP')
        self.assertEqual(cuerpo['destino']['nombre'], 'Tunja')
        self.assertEqual(cuerpo['grupos'][0]['trayecto_aplicado'], 'zonal')
        self.assertEqual(cuerpo['grupos'][0]['peso_bruto_kg'], '4.000')
        self.assertEqual(cuerpo['grupos'][0]['peso_facturable_kg'], 4)

    def test_ignora_precio_enviado_por_el_cliente(self):
        """Regresión del agujero de PayU: el precio del cliente no toca el total."""
        respuesta = self.cotizar({
            'id_municipio_destino': self.tunja.id_municipio,
            'items': [{'id_producto': self.queso.id_producto, 'cantidad': 5,
                       'precio': 1, 'peso_kg': '0.001', 'subtotal': 1}],
        })
        self.assertEqual(respuesta.status_code, 200)
        cuerpo = respuesta.json()
        self.assertEqual(cuerpo['totales']['subtotal_productos'], '150000.00')
        self.assertEqual(cuerpo['totales']['total'], '178100.00')

    def test_anonimo_puede_cotizar(self):
        self.assertNotIn('_auth_user_id', self.client.session)
        respuesta = self.cotizar({
            'id_municipio_destino': self.tunja.id_municipio,
            'items': [{'id_producto': self.queso.id_producto, 'cantidad': 1}],
        })
        self.assertEqual(respuesta.status_code, 200)

    def test_422_destino_no_soportado(self):
        respuesta = self.cotizar({
            'id_municipio_destino': self.leticia.id_municipio,
            'items': [{'id_producto': self.queso.id_producto, 'cantidad': 1}],
        })
        self.assertEqual(respuesta.status_code, 422)
        self.assertEqual(respuesta.json()['code'], 'destino_no_soportado')

    def test_422_producto_sin_peso(self):
        self.queso.peso_kg = None
        self.queso.save()
        respuesta = self.cotizar({
            'id_municipio_destino': self.tunja.id_municipio,
            'items': [{'id_producto': self.queso.id_producto, 'cantidad': 1}],
        })
        self.assertEqual(respuesta.status_code, 422)
        self.assertEqual(respuesta.json()['code'], 'producto_sin_peso')

    def test_422_producto_sin_origen(self):
        """Ni override en el producto ni municipio en el productor."""
        self.queso.id_municipio = None
        self.queso.save()
        self.productor_a.id_municipio = None
        self.productor_a.save()
        respuesta = self.cotizar({
            'id_municipio_destino': self.tunja.id_municipio,
            'items': [{'id_producto': self.queso.id_producto, 'cantidad': 1}],
        })
        self.assertEqual(respuesta.status_code, 422)
        self.assertEqual(respuesta.json()['code'], 'producto_sin_origen')

    def test_422_producto_sin_productor(self):
        self.queso.id_productor = None
        self.queso.save()
        respuesta = self.cotizar({
            'id_municipio_destino': self.tunja.id_municipio,
            'items': [{'id_producto': self.queso.id_producto, 'cantidad': 1}],
        })
        self.assertEqual(respuesta.status_code, 422)
        self.assertEqual(respuesta.json()['code'], 'producto_sin_productor')

    def test_municipio_del_productor_es_el_origen_por_defecto(self):
        """El producto no tiene override: despacha desde el municipio del productor."""
        self.assertIsNone(self.queso.id_municipio)
        respuesta = self.cotizar({
            'id_municipio_destino': self.tunja.id_municipio,
            'items': [{'id_producto': self.queso.id_producto, 'cantidad': 1}],
        })
        self.assertEqual(respuesta.status_code, 200)
        grupo = respuesta.json()['grupos'][0]
        self.assertEqual(grupo['municipio_origen'], 'Paipa')
        self.assertEqual(grupo['trayecto_aplicado'], 'zonal')

    def test_override_de_municipio_gana_sobre_el_productor(self):
        self.queso.id_municipio = self.tunja
        self.queso.save()
        respuesta = self.cotizar({
            'id_municipio_destino': self.tunja.id_municipio,
            'items': [{'id_producto': self.queso.id_producto, 'cantidad': 1}],
        })
        self.assertEqual(respuesta.status_code, 200)
        grupo = respuesta.json()['grupos'][0]
        self.assertEqual(grupo['municipio_origen'], 'Tunja')
        self.assertEqual(grupo['trayecto_aplicado'], 'urbano')

    def test_grupo_expone_productor_y_entrega(self):
        respuesta = self.cotizar({
            'id_municipio_destino': self.tunja.id_municipio,
            'items': [{'id_producto': self.queso.id_producto, 'cantidad': 1}],
        })
        cuerpo = respuesta.json()
        grupo = cuerpo['grupos'][0]
        self.assertEqual(grupo['id_productor'], self.productor_a.id_productor)
        self.assertEqual(grupo['productor'], 'Lácteos El Roble')
        self.assertEqual(grupo['entrega'], {'dias_min': 1, 'dias_max': 3})
        self.assertEqual(cuerpo['entrega'], {'dias_min': 1, 'dias_max': 3})

    def test_golden_multiproductor_yopal_sin_promocion(self):
        """Dos productores, destino Yopal. Sin promoción activa."""
        PromocionEnvio.objects.all().delete()
        respuesta = self.cotizar({
            'id_municipio_destino': self.yopal.id_municipio,
            'items': [
                {'id_producto': self.queso.id_producto, 'cantidad': 5},
                {'id_producto': self.sabajon.id_producto, 'cantidad': 1},
            ],
        })
        self.assertEqual(respuesta.status_code, 200)
        cuerpo = respuesta.json()
        self.assertEqual(len(cuerpo['grupos']), 2)

        roble, llano = cuerpo['grupos']
        self.assertEqual(roble['productor'], 'Lácteos El Roble')
        self.assertEqual(roble['trayecto_aplicado'], 'nacional')
        self.assertEqual(roble['peso_facturable_kg'], 4)
        self.assertEqual(roble['flete'], '32600.00')
        self.assertEqual(roble['sobreflete'], '3000.00')

        self.assertEqual(llano['productor'], 'Sabajón del Llano')
        self.assertEqual(llano['trayecto_aplicado'], 'territorial')
        self.assertEqual(llano['peso_facturable_kg'], 2)
        self.assertEqual(llano['flete'], '24650.00')
        self.assertEqual(llano['sobreflete'], '1700.00')

        totales = cuerpo['totales']
        self.assertEqual(totales['subtotal_productos'], '235000.00')
        self.assertEqual(totales['flete'], '57250.00')
        self.assertEqual(totales['sobreflete'], '4700.00')
        self.assertEqual(totales['descuento_envio'], '0.00')
        self.assertEqual(totales['envio'], '61950.00')
        self.assertEqual(totales['total'], '296950.00')
        self.assertEqual(cuerpo['entrega'], {'dias_min': 1, 'dias_max': 4})

    def test_golden_multiproductor_yopal_con_promocion(self):
        """Mismo carrito con la promoción activa: el flete se cubre, el sobreflete no."""
        respuesta = self.cotizar({
            'id_municipio_destino': self.yopal.id_municipio,
            'items': [
                {'id_producto': self.queso.id_producto, 'cantidad': 5},
                {'id_producto': self.sabajon.id_producto, 'cantidad': 1},
            ],
        })
        cuerpo = respuesta.json()
        self.assertTrue(cuerpo['promocion']['aplicada'])
        totales = cuerpo['totales']
        self.assertEqual(totales['descuento_envio'], '57250.00')
        self.assertEqual(totales['envio'], '4700.00')
        self.assertEqual(totales['envio'], totales['sobreflete'])
        self.assertEqual(totales['total'], '239700.00')

    def test_cotizacion_no_hace_n_mas_1(self):
        """Destino, productos, empaque y promoción: cuatro queries, no una por producto."""
        payload = {
            'id_municipio_destino': self.yopal.id_municipio,
            'items': [
                {'id_producto': self.queso.id_producto, 'cantidad': 5},
                {'id_producto': self.sabajon.id_producto, 'cantidad': 1},
            ],
        }
        with self.assertNumQueries(4):
            self.cotizar(payload)

    def test_422_origen_no_soportado(self):
        self.queso.id_municipio = self.sogamoso   # cobertura sólo como destino
        self.queso.save()
        respuesta = self.cotizar({
            'id_municipio_destino': self.tunja.id_municipio,
            'items': [{'id_producto': self.queso.id_producto, 'cantidad': 1}],
        })
        self.assertEqual(respuesta.status_code, 422)
        self.assertEqual(respuesta.json()['code'], 'origen_no_soportado')

    def test_422_empaque_no_configurado(self):
        ConfiguracionEmpaque.objects.all().delete()
        respuesta = self.cotizar({
            'id_municipio_destino': self.tunja.id_municipio,
            'items': [{'id_producto': self.queso.id_producto, 'cantidad': 1}],
        })
        self.assertEqual(respuesta.status_code, 422)
        self.assertEqual(respuesta.json()['code'], 'empaque_no_configurado')

    def test_producto_en_revision_no_cotiza(self):
        self.queso.estado = 'revisión'
        self.queso.save()
        respuesta = self.cotizar({
            'id_municipio_destino': self.tunja.id_municipio,
            'items': [{'id_producto': self.queso.id_producto, 'cantidad': 1}],
        })
        self.assertEqual(respuesta.status_code, 422)
        self.assertEqual(respuesta.json()['code'], 'producto_no_disponible')

    def test_producto_despublicado_no_cotiza(self):
        self.queso.deleted_at = timezone.now()
        self.queso.save()
        respuesta = self.cotizar({
            'id_municipio_destino': self.tunja.id_municipio,
            'items': [{'id_producto': self.queso.id_producto, 'cantidad': 1}],
        })
        self.assertEqual(respuesta.status_code, 422)
        self.assertEqual(respuesta.json()['code'], 'producto_no_disponible')

    def test_400_carrito_vacio(self):
        respuesta = self.cotizar({'id_municipio_destino': self.tunja.id_municipio, 'items': []})
        self.assertEqual(respuesta.status_code, 400)

    def test_400_cantidad_cero(self):
        respuesta = self.cotizar({
            'id_municipio_destino': self.tunja.id_municipio,
            'items': [{'id_producto': self.queso.id_producto, 'cantidad': 0}],
        })
        self.assertEqual(respuesta.status_code, 400)

    def test_400_producto_duplicado(self):
        respuesta = self.cotizar({
            'id_municipio_destino': self.tunja.id_municipio,
            'items': [{'id_producto': self.queso.id_producto, 'cantidad': 1},
                      {'id_producto': self.queso.id_producto, 'cantidad': 2}],
        })
        self.assertEqual(respuesta.status_code, 400)

    def test_override_de_frio_gana_sobre_la_categoria(self):
        self.categoria.requiere_frio = True
        self.categoria.save()
        self.queso.requiere_frio_override = False
        self.queso.save()
        respuesta = self.cotizar({
            'id_municipio_destino': self.tunja.id_municipio,
            'items': [{'id_producto': self.queso.id_producto, 'cantidad': 1}],
        })
        self.assertEqual(respuesta.json()['grupos'][0]['neveras'], 0)

        self.queso.requiere_frio_override = None
        self.queso.save()
        respuesta = self.cotizar({
            'id_municipio_destino': self.tunja.id_municipio,
            'items': [{'id_producto': self.queso.id_producto, 'cantidad': 1}],
        })
        self.assertEqual(respuesta.json()['grupos'][0]['neveras'], 1)


class DestinosAPITests(DatosEnvioMixin, TestCase):

    def setUp(self):
        self.crear_datos()
        self.url = reverse('envios-destinos')

    def test_lista_destinos_agrupados_por_departamento(self):
        respuesta = self.client.get(self.url)
        self.assertEqual(respuesta.status_code, 200)
        cuerpo = respuesta.json()
        # Boyacá y Casanare (Yopal); Amazonas no tiene cobertura como destino.
        self.assertEqual([d['nombre'] for d in cuerpo['departamentos']], ['Boyacá', 'Casanare'])
        boyaca = cuerpo['departamentos'][0]
        self.assertEqual([m['nombre'] for m in boyaca['municipios']],
                         ['Paipa', 'Pajarito', 'Sogamoso', 'Tunja'])
        self.assertEqual(boyaca['municipios'][3]['trayecto'], 'urbano')

    def test_omite_departamentos_sin_destinos(self):
        respuesta = self.client.get(self.url)
        nombres = [d['nombre'] for d in respuesta.json()['departamentos']]
        self.assertNotIn('Amazonas', nombres)

    def test_cachea_una_hora(self):
        respuesta = self.client.get(self.url)
        self.assertEqual(respuesta['Cache-Control'], 'public, max-age=3600')


class SeedShippingTests(TestCase):

    def setUp(self):
        self.boyaca = Departamento.objects.create(nombre='Boyacá')
        self.bogota_dc = Departamento.objects.create(nombre='Bogotá D.C.')
        Municipio.objects.create(id_departamento=self.boyaca, nombre='Tunja')
        Municipio.objects.create(id_departamento=self.boyaca, nombre='Güicán de la Sierra')
        Municipio.objects.create(id_departamento=self.bogota_dc, nombre='Bogotá D.C.')

    def sembrar(self, filas, **opciones):
        salida = StringIO()
        call_command('seed_shipping', file=escribir_cobertura(filas),
                     stdout=salida, stderr=salida, **opciones)
        return salida.getvalue()

    def test_match_con_tildes_y_alias(self):
        self.sembrar([
            {'municipio': 'Tunja', 'departamento': 'Boyacá', 'provincia': 'Centro',
             'distancia_km_tunja': 0.0, 'trayecto_origen': 'urbano', 'trayecto_destino': 'urbano'},
            {'municipio': 'Güicán', 'departamento': 'Boyacá', 'provincia': 'Gutiérrez',
             'distancia_km_tunja': 180.0, 'trayecto_origen': 'territorial',
             'trayecto_destino': 'territorial'},
            {'municipio': 'Bogotá D.C.', 'departamento': 'Cundinamarca', 'provincia': None,
             'distancia_km_tunja': 137.0, 'trayecto_origen': None, 'trayecto_destino': 'zonal'},
        ])
        self.assertEqual(CoberturaMunicipio.objects.count(), 3)
        self.assertTrue(CoberturaMunicipio.objects.filter(
            municipio__nombre='Güicán de la Sierra').exists())
        bogota = CoberturaMunicipio.objects.get(municipio__nombre='Bogotá D.C.')
        self.assertIsNone(bogota.trayecto_origen)
        self.assertEqual(bogota.trayecto_destino.codigo, 'zonal')

    def test_sin_match_revierte_todo(self):
        with self.assertRaises(CommandError):
            self.sembrar([
                {'municipio': 'Tunja', 'departamento': 'Boyacá', 'provincia': 'Centro',
                 'distancia_km_tunja': 0.0, 'trayecto_origen': 'urbano', 'trayecto_destino': 'urbano'},
                {'municipio': 'Municipio Inventado', 'departamento': 'Boyacá', 'provincia': '',
                 'distancia_km_tunja': None, 'trayecto_origen': 'zonal', 'trayecto_destino': 'zonal'},
            ])
        self.assertEqual(CoberturaMunicipio.objects.count(), 0)
        self.assertEqual(Trayecto.objects.count(), 0)

    def test_dry_run_no_escribe_y_sugiere(self):
        with self.assertRaises(CommandError):
            self.sembrar([
                {'municipio': 'Tunga', 'departamento': 'Boyacá', 'provincia': '',
                 'distancia_km_tunja': None, 'trayecto_origen': 'urbano', 'trayecto_destino': 'urbano'},
            ], dry_run=True)
        self.assertEqual(Trayecto.objects.count(), 0)

    def test_es_idempotente_y_no_pisa_la_configuracion(self):
        filas = [{'municipio': 'Tunja', 'departamento': 'Boyacá', 'provincia': 'Centro',
                  'distancia_km_tunja': 0.0, 'trayecto_origen': 'urbano', 'trayecto_destino': 'urbano'}]
        self.sembrar(filas)
        ConfiguracionEmpaque.objects.filter(activo=True).update(costo_nevera=Decimal('15000.00'))
        PromocionEnvio.objects.filter(activo=True).update(umbral_subtotal=Decimal('300000.00'))

        self.sembrar(filas)
        self.assertEqual(CoberturaMunicipio.objects.count(), 1)
        self.assertEqual(Trayecto.objects.count(), 5)
        self.assertEqual(
            ConfiguracionEmpaque.objects.get(activo=True).costo_nevera, Decimal('15000.00'))
        self.assertEqual(
            PromocionEnvio.objects.get(activo=True).umbral_subtotal, Decimal('300000.00'))

    def test_filas_retiradas_se_desactivan(self):
        self.sembrar([
            {'municipio': 'Tunja', 'departamento': 'Boyacá', 'provincia': 'Centro',
             'distancia_km_tunja': 0.0, 'trayecto_origen': 'urbano', 'trayecto_destino': 'urbano'},
            {'municipio': 'Güicán', 'departamento': 'Boyacá', 'provincia': 'Gutiérrez',
             'distancia_km_tunja': 180.0, 'trayecto_origen': 'territorial',
             'trayecto_destino': 'territorial'},
        ])
        self.sembrar([
            {'municipio': 'Tunja', 'departamento': 'Boyacá', 'provincia': 'Centro',
             'distancia_km_tunja': 0.0, 'trayecto_origen': 'urbano', 'trayecto_destino': 'urbano'},
        ])
        self.assertEqual(CoberturaMunicipio.objects.filter(activo=True).count(), 1)
        self.assertEqual(CoberturaMunicipio.objects.filter(activo=False).count(), 1)


class DatosDelTarifarioTests(TestCase):
    """El JSON versionado en el repo es la fuente de la tarifa: se valida su forma."""

    def test_seed_real_falla_sin_municipios_sembrados(self):
        salida = StringIO()
        with self.assertRaises(CommandError):
            # Sin `seed_locations` no hay municipios: la corrida debe fallar entera.
            call_command('seed_shipping', stdout=salida, stderr=salida)
        self.assertEqual(Trayecto.objects.count(), 0)

    def test_tarifario_trae_los_dias_de_entrega(self):
        """La hoja «Convenciones» del tarifario, versionada."""
        from shipping.management.commands.seed_shipping import DATA_DIR

        with (DATA_DIR / 'tarifario.json').open(encoding='utf-8') as archivo:
            filas = json.load(archivo)

        dias = {f['codigo']: (f['dias_entrega_min'], f['dias_entrega_max']) for f in filas}
        self.assertEqual(dias, {
            'urbano': (1, 1),
            'zonal': (1, 3),
            'nacional': (1, 4),
            'territorial': (1, 4),
            'especial': (8, 10),
        })

    def test_seed_sin_dias_falla_con_mensaje_claro(self):
        """Un tarifario desactualizado debe reventar, no sembrar 1-1 en silencio."""
        from shipping.management.commands.seed_shipping import Command

        fila = {
            'codigo': 'urbano', 'nombre': 'Urbano', 'jerarquia': 1,
            'valor_kilo_inicial': '8150', 'valor_kilo_adicional': '3850',
            'sobreflete_minimo': '800', 'porcentaje_sobreflete': '0.0200',
        }
        comando = Command()
        comando.dry_run = False
        with self.assertRaises(CommandError) as ctx:
            comando._sembrar_trayectos([fila])
        self.assertIn('dias_entrega_min', str(ctx.exception))
        self.assertEqual(Trayecto.objects.count(), 0)


class AliasMunicipiosTests(TestCase):
    """Pinea la tabla de alias contra los nombres reales de api-colombia.com, que es
    de donde `seed_locations` alimenta `locations.Municipio`."""

    # (municipio, departamento) como los escribe api-colombia ↔ como los escribe el .xlsx
    CASOS = [
        (('Buena Vista', 'Boyacá'), ('Buenavista', 'Boyacá')),
        (('Villa de Leyva', 'Boyacá'), ('Villa de Leyva', 'Boyacá')),
        (('Güicán', 'Boyacá'), ('Güicán', 'Boyacá')),
        (('Bogotá D.C.', 'Bogotá'), ('Bogotá D.C.', 'Cundinamarca')),
        (('San Andrés', 'San Andrés y Providencia'),
         ('San Andrés', 'San Andrés, Providencia y Santa Catalina')),
        (('Pasto', 'Nariño'), ('San Juan de Pasto', 'Nariño')),
        (('Cartagena de Indias', 'Bolívar'), ('Cartagena de Indias', 'Bolívar')),
        (('Cúcuta', 'Norte de Santander'), ('San José de Cúcuta', 'Norte de Santander')),
    ]

    def test_cada_caso_encuentra_su_municipio(self):
        departamentos = {}
        for (nombre_db, departamento_db), _ in self.CASOS:
            departamento = departamentos.get(departamento_db)
            if departamento is None:
                departamento = Departamento.objects.create(nombre=departamento_db)
                departamentos[departamento_db] = departamento
            Municipio.objects.create(id_departamento=departamento, nombre=nombre_db)

        # Homónimos reales que deben forzar el match por departamento, no por nombre único.
        santander = Departamento.objects.create(nombre='Santander')
        Municipio.objects.create(id_departamento=santander, nombre='San Andrés')

        filas = [
            {'municipio': municipio, 'departamento': departamento, 'provincia': '',
             'distancia_km_tunja': None, 'trayecto_origen': None, 'trayecto_destino': 'nacional'}
            for _, (municipio, departamento) in self.CASOS
        ]
        salida = StringIO()
        call_command('seed_shipping', file=escribir_cobertura(filas),
                     stdout=salida, stderr=salida)

        self.assertEqual(CoberturaMunicipio.objects.count(), len(self.CASOS))
        san_andres = CoberturaMunicipio.objects.get(municipio__nombre='San Andrés')
        self.assertEqual(san_andres.municipio.id_departamento.nombre, 'San Andrés y Providencia')
