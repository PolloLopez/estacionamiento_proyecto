# tests_roles.py — Tests de permisos por rol
from django.test import TestCase
from django.urls import reverse
from app_estacionamiento.models import Usuario, Municipio, Infraccion, Vehiculo, Subcuadra


class BaseRolesTest(TestCase):
    def setUp(self):
        self.municipio = Municipio.objects.create(nombre="Test")

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
            municipio=self.municipio, es_conductor=True, saldo=1000
        )


class AccesoAnonimo(BaseRolesTest):
    """Sin login, todo redirige al login."""

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


class AccesoPorRol(BaseRolesTest):
    """Cada rol solo accede a lo suyo."""

    def test_conductor_no_puede_acceder_panel_admin(self):
        self.client.force_login(self.conductor)
        response = self.client.get(reverse("panel_admin"))
        self.assertEqual(response.status_code, 403)

    def test_conductor_no_puede_verificar_vehiculo(self):
        self.client.force_login(self.conductor)
        response = self.client.get(reverse("inspectores_verificar_vehiculo"))
        self.assertEqual(response.status_code, 403)

    def test_inspector_no_puede_acceder_panel_admin(self):
        self.client.force_login(self.inspector)
        response = self.client.get(reverse("panel_admin"))
        self.assertEqual(response.status_code, 403)

    def test_vendedor_no_puede_verificar_vehiculo(self):
        self.client.force_login(self.vendedor)
        response = self.client.get(reverse("inspectores_verificar_vehiculo"))
        self.assertEqual(response.status_code, 403)

    def test_admin_puede_acceder_panel_admin(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("panel_admin"))
        self.assertEqual(response.status_code, 200)

    def test_inspector_puede_verificar_vehiculo(self):
        self.client.force_login(self.inspector)
        response = self.client.get(reverse("inspectores_verificar_vehiculo"))
        self.assertEqual(response.status_code, 200)


class FlujoConductorCompleto(BaseRolesTest):
    """Registro → estacionar → historial → finalizar."""

    def setUp(self):
        super().setUp()
        from app_estacionamiento.models import Subcuadra
        self.subcuadra = Subcuadra.objects.create(
            calle="San Martín", altura=100, municipio=self.municipio
        )

    def test_flujo_completo(self):
        self.client.force_login(self.conductor)

        # Estacionar
        response = self.client.post(
            reverse("usuarios_estacionar_vehiculo"),
            {"patente": "ZZZ111", "duracion": "1"}
        )
        self.assertEqual(response.status_code, 302)

        from app_estacionamiento.models import Estacionamiento
        est = Estacionamiento.objects.filter(vehiculo__patente="ZZZ111").first()
        self.assertIsNotNone(est)
        self.assertEqual(est.estado, "ACTIVO")

        # Historial
        response = self.client.get(reverse("usuarios_historial_estacionamientos"))
        self.assertEqual(response.status_code, 200)

        # Finalizar
        response = self.client.post(
            reverse("usuarios_finalizar_estacionamiento", args=[est.id])
        )
        self.assertEqual(response.status_code, 302)

        est.refresh_from_db()
        self.assertEqual(est.estado, "FINALIZADO")

    def test_no_puede_tener_dos_estacionamientos_activos(self):
        self.client.force_login(self.conductor)

        self.client.post(
            reverse("usuarios_estacionar_vehiculo"),
            {"patente": "DUP001", "duracion": "1"}
        )
        response = self.client.post(
            reverse("usuarios_estacionar_vehiculo"),
            {"patente": "DUP001", "duracion": "1"}
        )
        from app_estacionamiento.models import Estacionamiento
        activos = Estacionamiento.objects.filter(
            vehiculo__patente="DUP001", estado="ACTIVO"
        ).count()
        self.assertEqual(activos, 1)