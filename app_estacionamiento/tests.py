# app_estacionamiento/tests.py

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from app_estacionamiento.models import Vehiculo, Estacionamiento

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

        # debería redirigir
        self.assertEqual(response.status_code, 302)

        # se crea vehículo
        self.assertTrue(Vehiculo.objects.filter(patente="AAA111").exists())

        # se crea estacionamiento
        self.assertTrue(Estacionamiento.objects.exists())

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

        self.assertEqual(response.status_code, 200)


# 🚨 NUEVO TEST CLAVE
class VerificarVehiculoTest(TestCase):

    def setUp(self):
        self.inspector = User.objects.create_user(
            correo="inspector@test.com",
            password="123456",
            es_inspector=True
        )

    def test_patente_no_registrada_es_impaga(self):

        self.client.login(
            correo="inspector@test.com",
            password="123456"
        )

        response = self.client.post(
            reverse("inspectores_verificar_vehiculo"),
            {
                "patente": "NOEXISTE123"
            }
        )

        self.assertContains(response, "Impago")


# 🚨 TEST DE LOGIN POR ROL
class LoginRedirectTest(TestCase):

    def setUp(self):
        self.inspector = User.objects.create_user(
            correo="inspector@test.com",
            password="123456",
            es_inspector=True
        )

    def test_redirect_inspector(self):

        response = self.client.post(
            reverse("login"),
            {
                "correo": "inspector@test.com",
                "password": "123456"
            }
        )

        # debería redirigir al panel inspector
        self.assertRedirects(response, reverse("panel_inspectores"))