# app_estacionamiento/tests.py

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class EstacionamientoTest(TestCase):

    def setUp(self):

        self.user = User.objects.create_user(
            correo="conductor@test.com",
            password="123456",
            es_conductor=True,
            saldo=1000
        )

    def test_estacionar_view(self):

        login_ok = self.client.login(
            correo="conductor@test.com",
            password="123456"
        )

        self.assertTrue(login_ok)

        response = self.client.post(
            reverse("usuarios_estacionar_vehiculo"),
            {
                "patente": "AAA111",
                "duracion": "1"
            }
        )

        self.assertEqual(response.status_code, 302)

    def test_no_estaciona_sin_saldo(self):

        self.user.saldo = 0
        self.user.save()

        login_ok = self.client.login(
            correo="conductor@test.com",
            password="123456"
        )

        self.assertTrue(login_ok)

        response = self.client.post(
            reverse("usuarios_estacionar_vehiculo"),
            {
                "patente": "ZZZ999",
                "duracion": "2"
            }
        )

        self.assertContains(
            response,
            "Saldo insuficiente"
        )