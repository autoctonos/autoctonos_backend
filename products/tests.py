from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from locations.models import Departamento, Municipio
from producers.models import Productor

from .models import Producto, Categoria, ImagenProducto


class ProductDashboardTests(TestCase):
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
        self.assertContains(response, 'Dashboard de Productos')

    def test_admin_can_add_product_with_image(self):
        self.client.login(username='admin', password='pass')
        image_content = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!'
            b'\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02L\x01\x00;'
        )
        image = SimpleUploadedFile('test.gif', image_content, content_type='image/gif')
        response = self.client.post(
            reverse('product-dashboard'),
            {
                'id_categoria': self.categoria.id_categoria,
                'nombre': 'Prod',
                'descripcion': 'Desc',
                'precio': '10.00',
                'stock': 5,
                'presentacion': 'Un',
                'peso_kg': '0.800',
                'id_productor': self.productor.id_productor,
                'fabricante': 'Fab',
                'estado': 'aprobado',
                'image': image,
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Producto.objects.count(), 1)
        self.assertEqual(ImagenProducto.objects.count(), 1)
        self.assertEqual(Producto.objects.get().peso_kg, Decimal('0.800'))

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
                'precio': '15.00',
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
