from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model


class ProductDashboardTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username='admin', password='pass', is_staff=True
        )

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('product-dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response.url)

    def test_dashboard_loads_for_staff(self):
        self.client.login(username='admin', password='pass')
        response = self.client.get(reverse('product-dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Product Dashboard')
