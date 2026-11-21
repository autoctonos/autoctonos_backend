from unittest.mock import patch
import tempfile
from decimal import Decimal
from io import BytesIO, StringIO

from PIL import Image, ImageDraw

from django.core.management import call_command
from django.core.management.base import CommandError
from django.core.exceptions import ValidationError
from django.conf import settings as _settings
from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from locations.models import Departamento, Municipio
from producers.models import Productor

from .imagenes import (
    LADO_MAESTRO, normalizar_imagen_producto, tiene_fondo_damero, validar_imagen_producto,
)
from .models import Producto, Categoria, ImagenProducto


def _foto(nombre='foto.jpg', tamano=(1200, 900), fondo=(255, 255, 255), producto=(180, 40, 60),
          caja=None, fmt='JPEG', modo='RGB'):
    """Foto sintética: un rectángulo de color (el «producto») sobre un fondo."""
    imagen = Image.new(modo, tamano, fondo)
    ancho, alto = tamano
    caja = caja or (ancho // 10, alto // 10, ancho * 9 // 10, alto * 9 // 10)
    ImageDraw.Draw(imagen).rectangle(caja, fill=producto)
    salida = BytesIO()
    imagen.save(salida, format=fmt)
    tipo = {'JPEG': 'image/jpeg', 'PNG': 'image/png', 'WEBP': 'image/webp', 'GIF': 'image/gif'}[fmt]
    return SimpleUploadedFile(nombre, salida.getvalue(), content_type=tipo)


def _damero(tamano=(1200, 1200), cuadro=16, gris=(204, 204, 204)):
    imagen = Image.new('RGB', tamano, (255, 255, 255))
    dibujo = ImageDraw.Draw(imagen)
    for y in range(0, tamano[1], cuadro):
        for x in range(0, tamano[0], cuadro):
            if (x // cuadro + y // cuadro) % 2:
                dibujo.rectangle((x, y, x + cuadro - 1, y + cuadro - 1), fill=gris)
    dibujo.rectangle((300, 300, 900, 900), fill=(180, 40, 60))
    salida = BytesIO()
    imagen.save(salida, format='JPEG', quality=95)
    return SimpleUploadedFile('ruanas.jpg', salida.getvalue(), content_type='image/jpeg')


def _media_temporal():
    return override_settings(
        MEDIA_ROOT=tempfile.mkdtemp(),
        STORAGES={
            'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
            'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
        },
    )


# En tests no hay `collectstatic`: el storage con manifiesto falla en cualquier template
# que use {% static %} (admin, dashboard).
_STORAGES_SIN_MANIFEST = {
    **_settings.STORAGES,
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}


@override_settings(STORAGES=_STORAGES_SIN_MANIFEST)
class ProductDashboardTests(TestCase):
    """`/dashboard/`: la puerta de staff al panel de productos."""

    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(
            username='admin', password='pass', is_staff=True
        )
        self.user = User.objects.create_user(
            username='user', password='pass'
        )
        self.categoria = Categoria.objects.create(nombre='Cat1')
        self.departamento = Departamento.objects.create(nombre='Boyacá')
        self.municipio = Municipio.objects.create(
            id_departamento=self.departamento, nombre='Paipa'
        )
        self.productor = Productor.objects.create(
            nombre='Lácteos El Roble', descripcion='Quesos', telefono='3001112233',
            id_municipio=self.municipio,
        )

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('product-dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response.url)

    def test_dashboard_rejects_non_admin(self):
        self.client.login(username='user', password='pass')
        response = self.client.get(reverse('product-dashboard'))
        self.assertEqual(response.status_code, 403)

    def test_dashboard_loads_for_admin(self):
        self.client.login(username='admin', password='pass')
        response = self.client.get(reverse('product-dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Agregar producto')
        self.assertContains(response, 'Administración')

    def _post_producto(self, *fotos, **extra):
        datos = {
            'id_categoria': self.categoria.id_categoria,
            'nombre': 'Prod',
            'descripcion': 'Desc',
            'precio': '10.000',
            'stock': 5,
            'presentacion': 'Un',
            'peso_kg': '0.800',
            'id_productor': self.productor.id_productor,
            'fabricante': 'Fab',
            'estado': 'aprobado',
            'fotos': list(fotos),
            **extra,
        }
        return self.client.post(reverse('product-dashboard'), datos, follow=True)

    def test_admin_can_add_product_with_image(self):
        self.client.login(username='admin', password='pass')
        with _media_temporal():
            response = self._post_producto(_foto('test.png', (1200, 900), fmt='PNG'))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(Producto.objects.count(), 1)
            self.assertEqual(ImagenProducto.objects.count(), 1)
            producto = Producto.objects.get()
            self.assertEqual(producto.peso_kg, Decimal('0.800'))
            # El punto de miles no se lee como decimal.
            self.assertEqual(producto.precio, Decimal('10000'))
            self.assertEqual(producto.estado, 'aprobado')
            # Se guarda ya normalizada: JPEG cuadrado.
            guardada = ImagenProducto.objects.get().url_imagen
            self.assertTrue(guardada.name.endswith('.jpg'))
            with guardada.open('rb') as f:
                self.assertEqual(Image.open(f).size[0], Image.open(guardada.path).size[1])

    def test_dashboard_rechaza_foto_pequena(self):
        self.client.login(username='admin', password='pass')
        with _media_temporal():
            response = self._post_producto(_foto('mini.jpg', (500, 340)))
        self.assertEqual(Producto.objects.count(), 0)
        self.assertContains(response, 'lado más largo debe tener al menos 800 px')
        self.assertContains(response, '«mini.jpg»')

    def test_admin_can_update_product(self):
        self.client.login(username='admin', password='pass')
        producto = Producto.objects.create(
            id_categoria=self.categoria,
            nombre='Old',
            descripcion='Desc',
            precio='5.00',
            stock=2,
            estado='aprobado'
        )
        response = self.client.post(
            reverse('product-update', args=[producto.id_producto]),
            {
                'id_categoria': self.categoria.id_categoria,
                'nombre': 'New',
                'descripcion': 'New Desc',
                'precio': '15000',
                'stock': 10,
                'presentacion': 'Un',
                'peso_kg': '1.250',
                'id_productor': self.productor.id_productor,
                'fabricante': 'Fab',
                'estado': 'aprobado'
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        producto.refresh_from_db()
        self.assertEqual(producto.nombre, 'New')
        self.assertEqual(producto.peso_kg, Decimal('1.250'))

    def test_filtro_por_productor(self):
        otro = Productor.objects.create(nombre='Otro', descripcion='x', telefono='3000000000')
        for nombre, productor in (('Del roble', self.productor), ('Del otro', otro)):
            Producto.objects.create(id_categoria=self.categoria, nombre=nombre, descripcion='x',
                                    precio=1000, stock=1, id_productor=productor)
        self.client.login(username='admin', password='pass')
        response = self.client.get(reverse('product-dashboard'), {'productor': otro.pk})
        self.assertContains(response, 'Del otro')
        self.assertNotContains(response, 'Del roble')


@override_settings(STORAGES=_STORAGES_SIN_MANIFEST)
class FormularioProductorTests(TestCase):
    """`/panel/`: formulario abierto, sin cuenta. Solo crea, y todo queda en revisión."""

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.categoria = Categoria.objects.create(nombre='Lácteos')
        dep = Departamento.objects.create(nombre='Boyacá')
        self.municipio = Municipio.objects.create(id_departamento=dep, nombre='Paipa')
        self.roble = Productor.objects.create(
            nombre='Lácteos El Roble', descripcion='Quesos', telefono='3001112233',
            id_municipio=self.municipio,
        )
        self.otro = Productor.objects.create(
            nombre='Café La Esperanza', descripcion='Café', telefono='3005556677',
            id_municipio=self.municipio,
        )
        self.url = reverse('panel-productor')

    def _producto(self, productor, nombre, **extra):
        return Producto.objects.create(
            id_categoria=self.categoria, nombre=nombre, descripcion='x', precio=1000,
            stock=1, id_productor=productor, **extra
        )

    def _datos(self, *fotos, **extra):
        return {
            'id_productor': self.roble.pk,
            'id_categoria': self.categoria.id_categoria,
            'nombre': 'Queso campesino',
            'descripcion': 'Doble crema, hecho a mano.',
            'precio': '$ 18.000',
            'stock': 20,
            'presentacion': 'Un',
            'peso_kg': '0.6',
            'fotos': list(fotos),
            **extra,
        }

    def _dos_fotos(self):
        return _foto('a.jpg', (1200, 1200), producto=(200, 30, 30)), _foto('b.jpg', (1200, 1200), producto=(30, 30, 200))

    def test_abre_sin_login_y_sin_lista_hasta_elegir(self):
        self._producto(self.roble, 'Producto ya enviado XYZ')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Buscar productor')
        self.assertContains(response, 'Lácteos El Roble')  # en el selector
        self.assertNotContains(response, 'Producto ya enviado XYZ')
        self.assertIn('noindex', response['X-Robots-Tag'])

    def test_lista_del_productor_es_solo_consulta(self):
        self._producto(self.roble, 'Queso Paipa')
        self._producto(self.otro, 'Café de Pitalito')
        response = self.client.get(reverse('panel-productos'), {'productor': self.roble.pk})
        self.assertContains(response, 'Queso Paipa')
        self.assertNotContains(response, 'Café de Pitalito')
        self.assertNotContains(response, '/dashboard/')  # sin enlaces de edición
        self.assertContains(response, 'productos.autoctonos25@gmail.com')  # a dónde pedir cambios

    def test_crea_en_revision_con_el_productor_elegido_y_fotos_en_orden(self):
        with _media_temporal():
            response = self.client.post(self.url, self._datos(
                *self._dos_fotos(),
                orden_fotos='n1,n0',
                # Lo que el formulario abierto no deja elegir se ignora aunque llegue.
                estado='aprobado',
            ))
            self.assertEqual(response.status_code, 302)
            self.assertIn(f'productor={self.roble.pk}', response.url)
            producto = Producto.objects.get()
            self.assertEqual(producto.estado, 'revisión')
            self.assertEqual(producto.id_productor, self.roble)
            self.assertEqual(producto.precio, Decimal('18000'))
            fotos = list(producto.imagenproducto_set.all())
            self.assertEqual([f.orden for f in fotos], [0, 1])
            with fotos[0].url_imagen.open('rb') as f:
                r, g, b = Image.open(f).convert('RGB').getpixel((800, 800))
            self.assertGreater(b, r)  # la segunda subida («b», azul) quedó de portada

    def test_aviso_flotante_al_crear_con_foto_y_nombre(self):
        with _media_temporal():
            response = self.client.post(self.url, self._datos(*self._dos_fotos()), follow=True)
            portada = Producto.objects.get().imagenproducto_set.first()
        self.assertContains(response, 'id="flotante"')
        self.assertContains(response, '¡Listo! «Queso campesino» quedó en revisión.')
        self.assertContains(response, portada.url_imagen.url)
        # Se muestra una sola vez.
        self.assertNotContains(self.client.get(self.url), 'id="flotante"')

    def test_aviso_flotante_explica_el_error(self):
        response = self.client.post(self.url, self._datos(id_productor='', peso_kg=''))
        self.assertContains(response, 'No pudimos enviar el producto')
        self.assertContains(response, '<strong>Productor:</strong>')
        self.assertContains(response, 'Peso del paquete listo para enviar (kg):')

    def test_exige_elegir_productor(self):
        with _media_temporal():
            response = self.client.post(self.url, self._datos(*self._dos_fotos(), id_productor=''))
        self.assertEqual(Producto.objects.count(), 0)
        self.assertContains(response, 'Elige el productor de la lista')

    def test_productor_nuevo_se_registra_con_sus_datos(self):
        with _media_temporal():
            response = self.client.post(self.url, self._datos(
                *self._dos_fotos(), id_productor='', no_estoy='on',
                nuevo_nombre='Miel La Colmena', nuevo_telefono='+57 310 555 1234',
                nuevo_municipio=self.municipio.pk,
            ))
        self.assertEqual(response.status_code, 302)
        nuevo = Productor.objects.get(nombre='Miel La Colmena')
        self.assertEqual(nuevo.telefono, '3105551234')
        self.assertEqual(nuevo.id_municipio, self.municipio)
        self.assertEqual(Producto.objects.get().id_productor, nuevo)

    def test_productor_nuevo_valida_celular(self):
        # Corto, largo (el caso que reportó el usuario), prefijo inexistente (36) y fijo.
        for invalido in ('12345', '31939293845543', '3612345678', '6012345678'):
            with self.subTest(invalido), _media_temporal():
                response = self.client.post(self.url, self._datos(
                    *self._dos_fotos(), id_productor='', no_estoy='on',
                    nuevo_nombre='Miel La Colmena', nuevo_telefono=invalido, nuevo_municipio=self.municipio.pk,
                ))
                self.assertContains(response, 'El celular debe tener 10 dígitos')
        self.assertFalse(Productor.objects.filter(nombre='Miel La Colmena').exists())
        self.assertEqual(Producto.objects.count(), 0)

    def test_trampa_para_bots(self):
        with _media_temporal():
            self.client.post(self.url, self._datos(*self._dos_fotos(), sitio_web='http://spam'))
        self.assertEqual(Producto.objects.count(), 0)

    def test_limite_de_envios_por_hora(self):
        from . import panel
        with self.settings():
            for _ in range(panel.ENVIOS_POR_HORA):
                self.client.post(self.url, {})
            response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, 429)

    def test_exige_minimo_de_fotos(self):
        with _media_temporal():
            response = self.client.post(self.url, self._datos(_foto('a.jpg', (1200, 1200))))
        self.assertEqual(Producto.objects.count(), 0)
        self.assertContains(response, 'Sube al menos 2 fotos')
        self.assertContains(response, 'vuelve a elegir 1 foto')

    def test_exige_peso(self):
        with _media_temporal():
            response = self.client.post(self.url, self._datos(*self._dos_fotos(), peso_kg=''))
        self.assertEqual(Producto.objects.count(), 0)
        self.assertContains(response, 'aria-invalid="true"')

    def test_acepta_coma_decimal_y_limpia_cantidad_de_unidad(self):
        with _media_temporal():
            self.client.post(self.url, self._datos(
                *self._dos_fotos(), peso_kg='0,6', presentacion='Un', cantidad_presentacion='500',
            ))
        producto = Producto.objects.get()
        self.assertEqual(producto.peso_kg, Decimal('0.6'))
        self.assertIsNone(producto.cantidad_presentacion)

    def test_no_hay_rutas_de_edicion_publicas(self):
        producto = self._producto(self.roble, 'Queso')
        self.assertEqual(self.client.get(f'/panel/{producto.pk}/').status_code, 404)

    def test_api_devuelve_fotos_en_orden(self):
        with _media_temporal():
            producto = self._producto(self.roble, 'Queso', estado='aprobado')
            segunda = ImagenProducto.objects.create(id_producto=producto, url_imagen=_foto('a.jpg', (1200, 1200)), orden=1)
            portada = ImagenProducto.objects.create(id_producto=producto, url_imagen=_foto('b.jpg', (1200, 1200)), orden=0)
            ids = [i.pk for i in producto.imagenproducto_set.all()]
        self.assertEqual(ids, [portada.pk, segunda.pk])


class BackfillProductoresTests(TestCase):
    """`fabricante` es texto libre; el comando empareja pero nunca adivina."""

    def setUp(self):
        self.categoria = Categoria.objects.create(nombre='Lácteos')
        self.departamento = Departamento.objects.create(nombre='Boyacá')
        self.paipa = Municipio.objects.create(
            id_departamento=self.departamento, nombre='Paipa'
        )
        self.roble = Productor.objects.create(
            nombre='Lácteos El Roble', descripcion='Quesos', telefono='3001112233',
            id_municipio=self.paipa,
        )

    def crear_producto(self, nombre, fabricante, **extra):
        return Producto.objects.create(
            id_categoria=self.categoria, nombre=nombre, descripcion='x',
            precio=Decimal('1000.00'), stock=1, fabricante=fabricante,
            estado='aprobado', **extra
        )

    def correr(self, *args):
        salida = StringIO()
        call_command('backfill_productores', *args, stdout=salida, stderr=salida)
        return salida.getvalue()

    def test_asigna_por_nombre_normalizado(self):
        producto = self.crear_producto('Queso', '  LACTEOS EL ROBLE ')
        self.correr('--apply')
        producto.refresh_from_db()
        self.assertEqual(producto.id_productor, self.roble)

    def test_dry_run_no_escribe(self):
        producto = self.crear_producto('Queso', 'Lácteos El Roble')
        salida = self.correr()
        producto.refresh_from_db()
        self.assertIsNone(producto.id_productor)
        self.assertIn('no se escribió nada', salida)

    def test_ambiguo_no_asigna_y_reporta(self):
        Productor.objects.create(
            nombre='Lacteos el roble', descripcion='Homónimo', telefono='3009998877',
            id_municipio=self.paipa,
        )
        producto = self.crear_producto('Queso', 'Lácteos El Roble')
        salida = self.correr('--apply')
        producto.refresh_from_db()
        self.assertIsNone(producto.id_productor)
        self.assertIn('Ambiguos', salida)

    def test_sin_pareja_reporta_y_strict_falla(self):
        self.crear_producto('Queso', 'Quesos Inexistentes')
        with self.assertRaises(CommandError):
            self.correr('--apply', '--strict')

    def test_es_idempotente(self):
        producto = self.crear_producto('Queso', 'Lácteos El Roble')
        self.correr('--apply')
        salida = self.correr('--apply')
        producto.refresh_from_db()
        self.assertEqual(producto.id_productor, self.roble)
        self.assertIn('Asignados: 0', salida)

    def test_no_pisa_el_productor_ya_asignado(self):
        otro = Productor.objects.create(
            nombre='Otro', descripcion='x', telefono='3000000000', id_municipio=self.paipa,
        )
        producto = self.crear_producto('Queso', 'Lácteos El Roble', id_productor=otro)
        self.correr('--apply')
        producto.refresh_from_db()
        self.assertEqual(producto.id_productor, otro)

    def test_avisa_si_el_productor_no_tiene_municipio(self):
        self.roble.id_municipio = None
        self.roble.save()
        self.crear_producto('Queso', 'Lácteos El Roble')
        salida = self.correr('--apply')
        self.assertIn('no tiene municipio', salida)




SVG_QUESO = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M2 2h20"></path></svg>'


@override_settings(STORAGES=_STORAGES_SIN_MANIFEST)
class CategoriaIconoTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_superuser(
            username='admin-iconos', email='admin-iconos@example.com', password='x'
        )

    def test_slug_invalido_no_valida(self):
        from django.core.exceptions import ValidationError

        for malo in ('Cheese', 'cheese/../x', 'lucide:cheese', '-cheese'):
            with self.subTest(malo=malo), self.assertRaises(ValidationError):
                Categoria(nombre='Quesos', icono=malo).full_clean()
        Categoria(nombre='Quesos', icono='cake-slice').full_clean()
        Categoria(nombre='Otros', icono='').full_clean()

    def test_saneo_rechaza_contenido_activo(self):
        from .iconos import IconoError, sanear_svg

        for malo in (
            '<svg><script>alert(1)</script></svg>',
            '<svg><path d="M0" onload="x"/></svg>',
            '<svg><a href="javascript:x"><path d="M0"/></a></svg>',
            '<svg><path d="M0" fill="url(https://evil)"/></svg>',
            '<svg><foreignObject/></svg>',
        ):
            with self.subTest(malo=malo), self.assertRaises(IconoError):
                sanear_svg(malo)
        self.assertIn('<path d="M2 2h20">', sanear_svg('<svg viewBox="0 0 24 24"><path d="M2 2h20"/></svg>'))

    def test_api_expone_icono_y_svg_de_solo_lectura(self):
        Categoria.objects.create(nombre='Quesos', icono='cheese', icono_svg=SVG_QUESO)
        respuesta = self.client.get('/api/productos/categorias/')
        cuerpo = respuesta.json()
        fila = (cuerpo['results'] if isinstance(cuerpo, dict) else cuerpo)[0]
        self.assertEqual(fila['icono'], 'cheese')
        self.assertEqual(fila['icono_svg'], SVG_QUESO)

    def test_admin_descarga_svg_al_guardar(self):
        from unittest.mock import patch

        self.client.force_login(self.admin)
        url = reverse('admin:products_categoria_add')
        html = self.client.get(url).content.decode()
        self.assertIn('data-icp', html)

        with patch('products.admin.descargar_svg', return_value=SVG_QUESO) as descargar:
            respuesta = self.client.post(url, {'nombre': 'Quesos', 'icono': 'cheese'})
        self.assertEqual(respuesta.status_code, 302)
        descargar.assert_called_once_with('cheese')
        categoria = Categoria.objects.get(nombre='Quesos')
        self.assertEqual((categoria.icono, categoria.icono_svg), ('cheese', SVG_QUESO))

        # Sin cambiar el ícono no se vuelve a descargar; vaciarlo borra el SVG.
        cambio = reverse('admin:products_categoria_change', args=[categoria.pk])
        with patch('products.admin.descargar_svg') as descargar:
            self.client.post(cambio, {'nombre': 'Quesos', 'icono': 'cheese'})
            descargar.assert_not_called()
            self.client.post(cambio, {'nombre': 'Quesos', 'icono': ''})
        categoria.refresh_from_db()
        self.assertEqual((categoria.icono, categoria.icono_svg), ('', ''))

    def test_admin_muestra_error_si_iconify_falla(self):
        from unittest.mock import patch
        from .iconos import IconoError

        self.client.force_login(self.admin)
        with patch('products.admin.descargar_svg', side_effect=IconoError('sin conexión')):
            respuesta = self.client.post(
                reverse('admin:products_categoria_add'), {'nombre': 'Quesos', 'icono': 'cheese'}
            )
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'sin conexión')
        self.assertFalse(Categoria.objects.exists())


class EstandarFotoProductoTests(TestCase):
    """Toda foto queda cuadrada, sobre blanco, con el producto al mismo tamaño."""

    def abrir(self, contenido):
        return Image.open(BytesIO(contenido.read() if hasattr(contenido, 'read') else contenido))

    def test_rechaza_lo_que_no_tiene_arreglo(self):
        casos = {
            'imagen_pequena': _foto(tamano=(600, 400)),
            'imagen_alargada': _foto(tamano=(2400, 600)),
            'imagen_formato': _foto(fmt='GIF', tamano=(1000, 1000)),
            'imagen_damero': _damero(),
            'imagen_producto_lejano': _foto(tamano=(1600, 1200), caja=(700, 500, 900, 700)),
            'imagen_ilegible': SimpleUploadedFile('x.jpg', b'no soy una foto', content_type='image/jpeg'),
        }
        for codigo, archivo in casos.items():
            with self.subTest(codigo), self.assertRaises(ValidationError) as ctx:
                validar_imagen_producto(archivo)
            self.assertEqual(ctx.exception.code, codigo)

    def test_acepta_foto_correcta_y_fondos_lisos_sin_falso_positivo(self):
        validar_imagen_producto(_foto())
        for fondo in [(255, 255, 255), (220, 220, 220), (240, 232, 210)]:
            with self.subTest(fondo):
                validar_imagen_producto(_foto(fondo=fondo))
                imagen = Image.open(_foto(fondo=fondo))
                self.assertFalse(tiene_fondo_damero(imagen))

    def test_detecta_damero_de_transparencia_falsa(self):
        # 255/204 (Photoshop) y 255/238 (el damero tenue de la foto de Ruanas).
        for cuadro in (8, 16, 24):
            for gris in ((204, 204, 204), (238, 238, 238)):
                with self.subTest(cuadro=cuadro, gris=gris):
                    self.assertTrue(tiene_fondo_damero(Image.open(_damero(cuadro=cuadro, gris=gris))))

    def test_degradado_claro_no_es_damero(self):
        imagen = Image.linear_gradient('L').resize((1200, 1200)).point(lambda v: 200 + v * 55 // 255)
        self.assertFalse(tiene_fondo_damero(imagen.convert('RGB')))

    def test_encuadre_uniforme_sobre_fondo_blanco(self):
        """Producto lejos o cerca: termina ocupando lo mismo del cuadro."""
        lejos = _foto(tamano=(2400, 1800), caja=(800, 500, 1600, 1300))
        cerca = _foto(tamano=(1600, 1200), caja=(100, 100, 1500, 1100))
        ocupaciones = []
        for archivo in (lejos, cerca):
            validar_imagen_producto(archivo)
            imagen = self.abrir(normalizar_imagen_producto(archivo))
            self.assertEqual(imagen.format, 'JPEG')
            self.assertEqual(imagen.width, imagen.height)
            self.assertLessEqual(imagen.width, LADO_MAESTRO)
            caja = Image.eval(imagen.convert('L'), lambda v: 255 if v < 200 else 0).getbbox()
            ocupaciones.append((caja[2] - caja[0]) / imagen.width)
            self.assertEqual(imagen.getpixel((2, 2)), (255, 255, 255))
        for ocupacion in ocupaciones:
            self.assertAlmostEqual(ocupacion, 0.88, delta=0.02)

    def test_foto_ambientada_no_se_recorta(self):
        imagen = self.abrir(normalizar_imagen_producto(_foto(tamano=(1200, 900), fondo=(90, 120, 60))))
        self.assertEqual(imagen.size, (1200, 1200))
        self.assertGreater(sum(imagen.getpixel((600, 160))), 0)  # Franja blanca arriba…
        self.assertLess(sum(imagen.getpixel((5, 600))), 400)    # …y la foto intacta al centro.

    def test_transparencia_real_se_aplana_sobre_blanco(self):
        archivo = _foto(fmt='PNG', modo='RGBA', fondo=(0, 0, 0, 0), producto=(30, 90, 40, 255))
        imagen = self.abrir(normalizar_imagen_producto(archivo))
        self.assertEqual(imagen.mode, 'RGB')
        self.assertEqual(imagen.getpixel((2, 2)), (255, 255, 255))

    def test_nunca_agranda_y_reduce_lo_enorme(self):
        grande = self.abrir(normalizar_imagen_producto(_foto(tamano=(4000, 3000), fondo=(90, 120, 60))))
        self.assertEqual(grande.size, (LADO_MAESTRO, LADO_MAESTRO))
        chica = self.abrir(normalizar_imagen_producto(_foto(tamano=(900, 700), fondo=(90, 120, 60))))
        self.assertEqual(chica.size, (900, 900))

    def test_modelo_normaliza_al_guardar_y_no_toca_lo_guardado(self):
        categoria = Categoria.objects.create(nombre='Tejidos')
        producto = Producto.objects.create(
            id_categoria=categoria, nombre='Ruana', descripcion='d', precio='1', stock=1,
        )
        with _media_temporal():
            registro = ImagenProducto.objects.create(
                id_producto=producto, url_imagen=_foto('ruana.png', (1200, 900), fmt='PNG'),
            )
            nombre = registro.url_imagen.name
            self.assertTrue(nombre.endswith('.jpg'))
            registro.save()  # Re-guardar sin cambiar la foto no la re-procesa.
            self.assertEqual(registro.url_imagen.name, nombre)
            salida = StringIO()
            call_command('auditar_fotos_productos', stdout=salida)
            self.assertIn('ok=1 normalizable=0 rehacer=0', salida.getvalue())


class AsignarIconosCategoriasTests(TestCase):
    def test_asigna_por_nombre_sin_pisar_lo_elegido_en_el_admin(self):
        quesos = Categoria.objects.create(nombre='QUESOS')
        cafe = Categoria.objects.create(nombre='Café')
        elegida = Categoria.objects.create(nombre='Bebidas', icono='wine', icono_svg='<svg/>')
        rara = Categoria.objects.create(nombre='Otra cosa')
        with patch('products.management.commands.asignar_iconos_categorias.descargar_svg',
                   side_effect=lambda slug: f'<svg data-slug="{slug}"/>'):
            call_command('asignar_iconos_categorias', stdout=StringIO())  # Reporte: no escribe.
            quesos.refresh_from_db()
            self.assertEqual(quesos.icono, '')
            salida = StringIO()
            call_command('asignar_iconos_categorias', '--apply', stdout=salida)
        for categoria, slug in ((quesos, 'cheese'), (cafe, 'coffee'), (elegida, 'wine')):
            categoria.refresh_from_db()
            self.assertEqual(categoria.icono, slug)
        rara.refresh_from_db()
        self.assertEqual(rara.icono, '')
        self.assertIn('asignadas=2 sin_sugerencia=1 errores=0', salida.getvalue())


class CategoriaSlugTests(TestCase):
    def test_slug_desde_el_nombre_unico_y_estable(self):
        lacteos = Categoria.objects.create(nombre='Lácteos / Quesos')
        self.assertEqual(lacteos.slug, 'lacteos-quesos')
        self.assertEqual(Categoria.objects.create(nombre='EMBUTIDOS Y ENCURTIDOS').slug,
                         'embutidos-y-encurtidos')
        self.assertEqual(Categoria.objects.create(nombre='Lacteos quesos').slug, 'lacteos-quesos-2')
        # Renombrar no rompe los enlaces ya compartidos.
        lacteos.nombre = 'Lácteos'
        lacteos.save()
        lacteos.refresh_from_db()
        self.assertEqual(lacteos.slug, 'lacteos-quesos')

    def test_slug_invalido_se_rechaza(self):
        for malo in ('Bebidas', 'cafe especial', 'café', '-bebidas'):
            with self.subTest(malo), self.assertRaises(ValidationError):
                Categoria(nombre='X', slug=malo).full_clean()

    def test_api_expone_slug_y_filtra_por_el(self):
        quesos = Categoria.objects.create(nombre='Quesos')
        Producto.objects.create(id_categoria=quesos, nombre='Pera', descripcion='d',
                                precio='1', stock=1, estado='aprobado')
        cuerpo = self.client.get('/api/productos/categorias/').json()
        self.assertEqual(cuerpo['results'][0]['slug'], 'quesos')
        producto = Producto.objects.get()
        detalle = self.client.get(f'/api/productos/producto-detalle/{producto.id_producto}/').json()
        self.assertEqual((detalle['categoria_nombre'], detalle['categoria_slug']), ('Quesos', 'quesos'))
        for valor in ('quesos', 'QUESOS', str(quesos.id_categoria)):
            with self.subTest(valor):
                respuesta = self.client.get('/api/productos/productos_categoria/',
                                            {'id_categoria': valor})
                self.assertEqual(len(respuesta.json()), 1)
