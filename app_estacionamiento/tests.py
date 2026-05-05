# app_estacionamiento/tests.py

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()

class EstacionamientoTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            correo="test@test.com",
            password="123456"
        )

    def test_estacionar_view(self):
        self.client.login(correo="test@test.com", password="123456")

        response = self.client.post(
            reverse("usuarios_estacionar_vehiculo"),
            {
                "patente": "AAA111",
                "duracion": "1"
            }
        )

        self.assertEqual(response.status_code, 302)  # redirect OK