# app_estacionamiento/tests_roles.py
# Tests de permisos por rol y flujo completo del conductor

from django.test import TestCase
from django.urls import reverse
from app_estacionamiento.models import (
    Usuario, Municipio, Subcuadra, Estacionamiento
)


class BaseRolesTest(TestCase):

    def setUp(self):
        self.municipio = Municipio.objects.create(nombre="Test")

        self.subcuadra = Subcuadra.objects.create(
            calle="San Martín", altura=100, municipio=self.municipio
        )

        self.admin = Usuario.objects.create_user(
            correo="admin@test.com", password="123456",
            municipio=self.municipio, es_admin=True, es_conductor=False
        )
        self.inspector = Usuario.objects.create_user(
            correo="inspector@test.com", password="123456",
            municipio=self.municipio, es_inspector=True, es_conductor=False
        )
        self.vendedor = Usuario.objects.create_user(
            correo="vendedor@test.com", password="123456",
            municipio=self.municipio, es_vendedor=True, es_conductor=False
        )
        self.conductor = Usuario.objects.create_user(
            correo="conductor@test.com", password="123456",
            municipio=self.municipio, es_conductor=True, saldo=1000,
            first_name="Test",  # evita redirección del middleware (conductor sin nombre)
        )


# =====================================================
# 🔒 ACCESO ANÓNIMO
# =====================================================

class AccesoAnonimoTest(BaseRolesTest):
    """Sin login, todo debe redirigir al login."""

    def test_panel_admin_requiere_login(self):
        response = self.client.get(reverse("panel_admin"))
        self.assertRedirects(response, reverse("login"))

    def test_panel_inspectores_requiere_login(self):
        response = self.client.get(reverse("panel_inspectores"))
        self.assertRedirects(response, reverse("login"))

    def test_verificar_vehiculo_requiere_login(self):
        response = self.client.get(reverse("inspectores_verificar_vehiculo"))
        self.assertRedirects(response, reverse("login"))

    def test_cerrar_caja_requiere_login(self):
        response = self.client.post(reverse("inspectores_cerrar_caja"))
        self.assertRedirects(response, reverse("login"))

    def test_estacionar_requiere_login(self):
        response = self.client.post(reverse("usuarios_estacionar_vehiculo"))
        self.assertRedirects(response, reverse("login"))


# =====================================================
# 🎭 ACCESO POR ROL
# =====================================================

class AccesoPorRolTest(BaseRolesTest):
    """Cada rol solo accede a lo que le corresponde."""

    def test_conductor_no_puede_ver_panel_admin(self):
        self.client.force_login(self.conductor)
        response = self.client.get(reverse("panel_admin"))
        self.assertEqual(response.status_code, 403)

    def test_conductor_no_puede_verificar_vehiculo(self):
        self.client.force_login(self.conductor)
        response = self.client.get(reverse("inspectores_verificar_vehiculo"))
        self.assertEqual(response.status_code, 403)

    def test_inspector_no_puede_ver_panel_admin(self):
        self.client.force_login(self.inspector)
        response = self.client.get(reverse("panel_admin"))
        self.assertEqual(response.status_code, 403)

    def test_vendedor_no_puede_verificar_vehiculo(self):
        self.client.force_login(self.vendedor)
        response = self.client.get(reverse("inspectores_verificar_vehiculo"))
        self.assertEqual(response.status_code, 403)

    def test_admin_puede_ver_panel_admin(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("panel_admin"))
        self.assertEqual(response.status_code, 200)

    def test_inspector_puede_verificar_vehiculo(self):
        self.client.force_login(self.inspector)
        response = self.client.get(reverse("inspectores_verificar_vehiculo"))
        self.assertEqual(response.status_code, 200)

    def test_vendedor_puede_ver_su_panel(self):
        self.client.force_login(self.vendedor)
        response = self.client.get(reverse("panel_vendedor"))
        self.assertEqual(response.status_code, 200)


# =====================================================
# 🚗 FLUJO COMPLETO CONDUCTOR
# =====================================================

class FlujoConductorCompletoTest(BaseRolesTest):
    """Estacionar → historial → finalizar."""

    def test_flujo_completo(self):
        self.client.force_login(self.conductor)

        # 1. Estacionar
        response = self.client.post(
            reverse("usuarios_estacionar_vehiculo"),
            {"patente": "ZZZ111", "duracion": "1"}
        )
        self.assertEqual(response.status_code, 302)

        est = Estacionamiento.objects.filter(vehiculo__patente="ZZZ111").first()
        self.assertIsNotNone(est, "El estacionamiento no se creó")
        self.assertEqual(est.estado, "ACTIVO")

        # 2. Historial
        response = self.client.get(reverse("usuarios_historial_estacionamientos"))
        self.assertEqual(response.status_code, 200)

        # 3. Finalizar
        response = self.client.post(
            reverse("usuarios_finalizar_estacionamiento", args=[est.id])
        )
        self.assertEqual(response.status_code, 302)

        est.refresh_from_db()
        self.assertEqual(est.estado, "FINALIZADO")

    def test_saldo_se_descuenta_al_estacionar(self):
        self.client.force_login(self.conductor)
        saldo_inicial = self.conductor.saldo

        self.client.post(
            reverse("usuarios_estacionar_vehiculo"),
            {"patente": "AAA999", "duracion": "2"}
        )

        self.conductor.refresh_from_db()
        self.assertLess(self.conductor.saldo, saldo_inicial)

    def test_no_puede_tener_dos_estacionamientos_activos(self):
        self.client.force_login(self.conductor)

        self.client.post(
            reverse("usuarios_estacionar_vehiculo"),
            {"patente": "DUP001", "duracion": "1"}
        )
        self.client.post(
            reverse("usuarios_estacionar_vehiculo"),
            {"patente": "DUP001", "duracion": "1"}
        )

        activos = Estacionamiento.objects.filter(
            vehiculo__patente="DUP001", estado="ACTIVO"
        ).count()
        self.assertEqual(activos, 1)

    def test_conductor_sin_saldo_redirige_a_deuda(self):
        self.conductor.saldo = 0
        self.conductor.save()

        self.client.force_login(self.conductor)
        response = self.client.post(
            reverse("usuarios_estacionar_vehiculo"),
            {"patente": "SIN001", "duracion": "1"}
        )
        self.assertRedirects(response, reverse("consultar_deuda"))
