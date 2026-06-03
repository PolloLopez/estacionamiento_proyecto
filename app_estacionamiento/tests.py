# app_estacionamiento/tests.py
from django.test import TestCase
from django.urls import reverse
from decimal import Decimal
from django.db.models import Sum

from app_estacionamiento.models import (
    Vehiculo, Subcuadra, Infraccion,
    Usuario, Estacionamiento,
    MovimientoCaja, Municipio, CierreCaja,
    VehiculoUsuario, VerificacionInspector
)

from app_estacionamiento.services_infracciones import (
    crear_infraccion, ErrorInfraccion
)

from app_estacionamiento.services_verificacion import (
    verificar_estado_vehiculo
)

from app_estacionamiento.domain.enums import EstadoVehiculo

from app_estacionamiento.use_cases.cobrar_estacionamiento import ejecutar as cobrar_estacionamiento


# =====================================================
# 🧱 BASE
# =====================================================

class BaseTestCase(TestCase):

    def setUp(self):
        self.municipio = Municipio.objects.create(
            nombre="TestCity"
        )

        self.usuario = Usuario.objects.create_user(
            correo="inspector@test.com",
            password="123456",
            municipio=self.municipio,
            es_inspector=True
        )

        self.subcuadra = Subcuadra.objects.create(
            calle="Calle Test",
            altura=100,
            municipio=self.municipio
        )

# =====================================================
# 🚗 ESTACIONAMIENTO
# =====================================================

class EstacionamientoTest(BaseTestCase):

    def setUp(self):
        super().setUp()

        self.user = Usuario.objects.create_user(
            correo="conductor@test.com",
            password="123456",
            es_conductor=True,
            saldo=1000,
            municipio=self.municipio
        )

        self.vehiculo = Vehiculo.objects.create(
            patente="AAA111",
            municipio=self.municipio
        )

    def test_estacionar_view(self):
        self.client.login(correo="conductor@test.com", password="123456")

        response = self.client.post(
            reverse("usuarios_estacionar_vehiculo"),
            {"patente": "AAA111", "duracion": "1"}
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Vehiculo.objects.filter(patente="AAA111").exists())
        self.assertTrue(Estacionamiento.objects.exists())

    def test_no_estaciona_sin_saldo(self):
        self.user.saldo = 0
        self.user.save()

        self.client.login(correo="conductor@test.com", password="123456")

        response = self.client.post(
            reverse("usuarios_estacionar_vehiculo"),
            {"patente": "ZZZ999", "duracion": "2"}
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("consultar_deuda"))


# =====================================================
# 💰 CAJA
# =====================================================

class CajaInspectorTest(BaseTestCase):

    def setUp(self):
        super().setUp()

        self.inspector = self.usuario
        self.inspector.saldo_operativo = 1000
        self.inspector.save()

    def test_calculo_a_rendir(self):
    
        MovimientoCaja.objects.create(
            usuario=self.inspector,
            monto=Decimal("500"),
            tipo="ingreso",
            descripcion="Cobro calle"
        )
    
        total = (
            MovimientoCaja.objects
            .filter(
                usuario=self.inspector,
                tipo="ingreso"
            )
            .aggregate(total=Sum("monto"))["total"]
            or Decimal("0")
        )
    
        self.assertEqual(total, Decimal("500"))


# =====================================================
# 🔍 VERIFICACIÓN
# =====================================================

class VerificacionTest(BaseTestCase):

    def setUp(self):
        super().setUp()

        self.vehiculo = Vehiculo.objects.create(
            patente="BBB222",
            municipio=self.municipio
        )

        VehiculoUsuario.objects.create(
            usuario=self.usuario,
            vehiculo=self.vehiculo
        )

    def test_no_registrado(self):
        resultado = verificar_estado_vehiculo(
            "AAA111", 
            self.usuario,
            self.subcuadra
            )
        self.assertEqual(resultado.estado, EstadoVehiculo.NO_REGISTRADO)

    def test_exento_total(self):
        self.vehiculo.exento_global = True
        self.vehiculo.save()

        resultado = verificar_estado_vehiculo(
            self.vehiculo.patente,
            self.usuario,
            self.subcuadra
        )

        self.assertEqual(resultado.estado, EstadoVehiculo.EXENTO_TOTAL)

    def test_exento_parcial(self):
        self.vehiculo.subcuadras_exentas.add(self.subcuadra)

        resultado = verificar_estado_vehiculo(
            self.vehiculo.patente,
            self.usuario,
            self.subcuadra
        )

        self.assertEqual(resultado.estado, EstadoVehiculo.EXENTO_PARCIAL)

    def test_pagado(self):
        Estacionamiento.objects.create(
            vehiculo=self.vehiculo,
            usuario=self.usuario,
            estado="ACTIVO",
            subcuadra=self.subcuadra,
        )

        resultado = verificar_estado_vehiculo(
            self.vehiculo.patente,
            self.usuario,
            self.subcuadra
        )

        self.assertEqual(resultado.estado, EstadoVehiculo.PAGADO)

    def test_pendiente_pago_por_tolerancia(self):

        VerificacionInspector.objects.create(
            vehiculo=self.vehiculo,
            inspector=self.usuario,
            subcuadra=self.subcuadra,
            resultado="verificacion"
        )

        resultado = verificar_estado_vehiculo(
            self.vehiculo.patente,
            self.usuario,
            self.subcuadra
        )

        self.assertEqual(resultado.estado, EstadoVehiculo.PENDIENTE_PAGO)

    def test_impago(self):
        resultado = verificar_estado_vehiculo(
            self.vehiculo.patente,
            self.usuario,
            self.subcuadra
        )

        self.assertEqual(resultado.estado, EstadoVehiculo.IMPAGO)

# =====================================================
# 🚨 INFRACCIONES
# =====================================================

class CrearInfraccionTest(BaseTestCase):

    def setUp(self):
        super().setUp()

        self.vehiculo = Vehiculo.objects.create(
            patente="ABC123",
            municipio=self.municipio
        )

        VehiculoUsuario.objects.create(
            usuario=self.usuario,
            vehiculo=self.vehiculo
        )

        self.subcuadra = Subcuadra.objects.create(
            calle="12",
            altura=34,
            municipio=self.municipio
        )

    def test_crea_infraccion_ok(self):
        infraccion = crear_infraccion(
            patente="ABC123",
            subcuadra_id=self.subcuadra.id,
            inspector=self.usuario
        )

        self.assertIsNotNone(infraccion)

    def test_no_permite_exento_total(self):
        self.vehiculo.exento_global = True
        self.vehiculo.save()

        with self.assertRaises(ErrorInfraccion):
            crear_infraccion(
                patente="ABC123",
                subcuadra_id=self.subcuadra.id,
                inspector=self.usuario
            )


# =====================================================
# 🔐 LOGIN
# =====================================================

class LoginRedirectTest(BaseTestCase):

    def setUp(self):
        super().setUp()

        self.inspector = self.usuario

    def test_redirect_inspector(self):
        response = self.client.post(
            reverse("login"),
            {"correo": "inspector@test.com", "password": "123456"}
        )

        self.assertRedirects(response, reverse("panel_inspectores"))


# =====================================================
# 🧾 CAJA
# =====================================================

class CierreCajaTest(BaseTestCase):

    def setUp(self):
        super().setUp()

        self.inspector = self.usuario
        self.inspector.saldo_operativo = 1000
        self.inspector.save()

    def test_cierre_caja(self):
        self.client.login(
            correo="inspector@test.com",
            password="123456"
        )

        cobrar_estacionamiento(
            inspector=self.inspector,
            monto=Decimal("500"),
            descripcion="Cobro calle"
        )

        response = self.client.post(reverse("inspectores_cerrar_caja"))

        self.assertEqual(response.status_code, 302)


# =====================================================
# 🌐 URLS
# =====================================================

class UrlsTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.admin = Usuario.objects.create_user(
            correo="admin@test.com",
            password="12345",
            municipio=self.municipio,
            es_admin=True
        )

        self.inspector = Usuario.objects.create_user(
            correo="inspector2@test.com",
            password="123456",
            municipio=self.municipio,
            es_inspector=True
        )

        self.vendedor = Usuario.objects.create_user(
            correo="vendedor2@test.com",
            password="123456",
            municipio=self.municipio,
            es_vendedor=True
        )

        self.conductor = Usuario.objects.create_user(
            correo="conductor2@test.com",
            password="123456",
            municipio=self.municipio,
            es_conductor=True
        )

    def test_root_redirect_admin(self):
        self.client.force_login(self.admin)
        response = self.client.get("/")
        self.assertRedirects(response, reverse("panel_admin"))

    def test_root_redirect_inspector(self):
        self.client.force_login(self.inspector)
        response = self.client.get("/")
        self.assertRedirects(response, reverse("panel_inspectores"))

    def test_root_redirect_vendedor(self):
        self.client.force_login(self.vendedor)
        response = self.client.get("/")
        self.assertRedirects(response, reverse("panel_vendedor"))

    def test_root_redirect_conductor(self):
        self.client.force_login(self.conductor)
        response = self.client.get("/")
        self.assertRedirects(response, reverse("inicio_usuarios"))