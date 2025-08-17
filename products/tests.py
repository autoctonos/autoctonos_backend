from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from .models import Producto, Categoria, ImagenProducto


class ProductDashboardTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(
            username='admin', password='pass', is_staff=True, is_superuser=True
        )
        self.user = User.objects.create_user(
            username='user', password='pass'
        )
        self.categoria = Categoria.objects.create(nombre='Cat1')

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
        self.assertContains(response, 'Product Dashboard')

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
                'estado': 'aprobado',
                'image': image,
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Producto.objects.count(), 1)
        self.assertEqual(ImagenProducto.objects.count(), 1)

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
                'estado': 'aprobado'
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        producto.refresh_from_db()
        self.assertEqual(producto.nombre, 'New')
