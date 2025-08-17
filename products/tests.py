from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from users.models import Usuario
from .models import Post


class DashboardCreateProductTests(APITestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user(
            username="testuser", password="testpass123"
        )

    def test_product_created_in_review_state(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("dashboard-create-product")
        data = {
            "nombre": "Producto de prueba",
            "descripcion": "Descripcion",
            "precio": "10.00",
            "stock": 3,
        }
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        post = Post.objects.get(id_post=response.data["id_post"])
        self.assertEqual(post.estado, "revisión")
        self.assertEqual(post.mensaje, "En revisión")

