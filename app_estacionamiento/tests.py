from urllib import response

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.db.models import Sum
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from app_estacionamiento.domain.verificacion import ResultadoVerificacion
from app_estacionamiento.domain.enums import EstadoVehiculo
from app_estacionamiento.models import (
    Vehiculo, Subcuadra, Infraccion,
    Usuario, Estacionamiento,
    MovimientoCaja, Municipio
)
from app_estacionamiento.models import CierreCaja

from app_estacionamiento.services_infracciones import (
    crear_infraccion, ErrorInfraccion
)

from app_estacionamiento.services_verificacion import (
    verificar_estado_vehiculo
)
from app_estacionamiento.use_cases import cobrar_estacionamiento
from app_estacionamiento.use_cases.cobrar_estacionamiento import ejecutar as cobrar_estacionamiento


User = get_user_model()


# =====================================================
# 🧱 BASE + MIXINS (PRIMERO SIEMPRE)
# =====================================================

class BaseTestCase(TestCase):

    def setUp(self):
        self.municipio = Municipio.objects.create(nombre="TestCity")

        self.usuario = Usuario.objects.create(
            email="inspector@test.com",
            municipio=self.municipio
        )

        self.subcuadra = Subcuadra.objects.create(
            calle="Calle Falsa",
            altura=123,
            municipio=self.municipio
        )


class ResultadoAssertionsMixin:

    def assertEsMultable(self, resultado):
        self.assertFalse(resultado.estacionamiento_activo)
        self.assertIsNotNone(resultado.registrar_infraccion_url)
        self.assertTrue(resultado.necesita_infraccion())

    def assertNoEsMultable(self, resultado):
        self.assertTrue(resultado.estacionamiento_activo)
        self.assertIsNone(resultado.registrar_infraccion_url)
        self.assertFalse(resultado.necesita_infraccion())

    def assertEstado(self, resultado, esperado: EstadoVehiculo):
        self.assertEqual(resultado.estado, esperado)

# =====================================================
# 🚗 ESTACIONAMIENTO
# =====================================================

class EstacionamientoTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            correo="conductor@test.com",
            password="123456",
            es_conductor=True,
            saldo=1000
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
# 💰 CAJA INSPECTOR
# =====================================================

class CajaInspectorTest(TestCase):

    def setUp(self):
        self.inspector = User.objects.create_user(
            correo="inspector@test.com",
            password="123456",
            es_inspector=True,
            saldo_operativo=1000
        )

    def test_calculo_a_rendir(self):

        MovimientoCaja.objects.all().delete()

        MovimientoCaja.objects.create(
            usuario=self.inspector,
            monto=Decimal("500"),
            tipo="ingreso",
            descripcion="Cobro calle"
        )

        total = MovimientoCaja.objects.filter(
            usuario=self.inspector,
            tipo="ingreso"
        ).aggregate(total=Sum("monto"))["total"] or Decimal("0")

        self.assertEqual(total, Decimal("500"))

    def test_descuenta_saldo_inspector(self):
        self.client.login(correo="inspector@test.com", password="123456")

        self.client.post(
            reverse("inspectores_registrar_estacionamiento_manual"),
            {"patente": "TEST123", "duracion": "2"}
        )

        self.inspector.refresh_from_db()
        self.assertEqual(self.inspector.saldo_operativo, 1200)


# =====================================================
# 🔍 VERIFICACIÓN (DATACLASS READY)
# =====================================================

class VerificacionTest(BaseTestCase, ResultadoAssertionsMixin):

    def test_no_registrado(self):
        resultado = verificar_estado_vehiculo("AAA111", self.usuario)

        self.assertEqual(resultado.patente, "AAA111")
        self.assertEstado(resultado, EstadoVehiculo.NO_REGISTRADO)
        self.assertEsMultable(resultado)


    def test_exento_total(self):
        vehiculo = Vehiculo.objects.create(
        patente="BBB222",
        municipio=self.municipio,
        exento_global=True
    )

        resultado = verificar_estado_vehiculo(vehiculo.patente, self.usuario)

        self.assertEstado(resultado, EstadoVehiculo.EXENTO_TOTAL)
        self.assertNoEsMultable(resultado)


    def test_exento_parcial(self):
        vehiculo = Vehiculo.objects.create(
            patente="CCC333",
            municipio=self.municipio
        )

        vehiculo.subcuadras_exentas.add(self.subcuadra)

        resultado = verificar_estado_vehiculo(vehiculo.patente, self.usuario)

        self.assertEstado(resultado, EstadoVehiculo.EXENTO_PARCIAL)
        self.assertEsMultable(resultado)

        self.assertIsNotNone(resultado.subcuadras_exentas)
        self.assertTrue(resultado.subcuadras_exentas.exists())
        
    def test_pagado(self):
        vehiculo = Vehiculo.objects.create(
            patente="DDD444",
            municipio=self.municipio
        )

        Estacionamiento.objects.create(
            vehiculo=vehiculo,
            municipio=self.municipio,
            activo=True,
            subcuadra=self.subcuadra,
            registrado_por=self.usuario
        )

        resultado = verificar_estado_vehiculo(vehiculo.patente, self.usuario)

        self.assertEstado(resultado, EstadoVehiculo.PAGADO)
        self.assertNoEsMultable(resultado)

    def test_impago(self):
        vehiculo = Vehiculo.objects.create(
            patente="EEE555",
            municipio=self.municipio
        )

        resultado = verificar_estado_vehiculo(vehiculo.patente, self.usuario)

        self.assertEstado(resultado, EstadoVehiculo.IMPAGO)
        self.assertEsMultable(resultado)

    def test_resultado_tiene_estructura_correcta(self):
        resultado = verificar_estado_vehiculo("ZZZ999", self.usuario)

        self.assertTrue(hasattr(resultado, "patente"))
        self.assertTrue(hasattr(resultado, "estado"))
        self.assertTrue(hasattr(resultado, "estacionamiento_activo"))
        self.assertTrue(hasattr(resultado, "registrar_infraccion_url"))
        self.assertTrue(hasattr(resultado, "necesita_infraccion"))

    def test_flujo_real_impago(self):
        vehiculo = Vehiculo.objects.create(
            patente="FFF666",
            municipio=self.municipio
        )

        resultado = verificar_estado_vehiculo(vehiculo.patente, self.usuario)

        self.assertEsMultable(resultado)
        self.assertTrue(resultado.necesita_infraccion())

    def test_flujo_inspector_completo(self):
        vehiculo = Vehiculo.objects.create(
            patente="TEST123",
            municipio=self.municipio
        )

        resultado = verificar_estado_vehiculo("TEST123", self.usuario)

        self.assertEqual(resultado.patente, "TEST123")
        self.assertTrue(hasattr(resultado, "estado"))
        self.assertTrue(hasattr(resultado, "necesita_infraccion"))

    def test_flujo_verificacion_real(self):

        vehiculo = Vehiculo.objects.create(
            patente="TEST123",
            municipio=self.municipio
        )

        # caso sin nada → IMPAGO
        r = verificar_estado_vehiculo("TEST123", self.usuario)
        self.assertEqual(r.estado, EstadoVehiculo.IMPAGO)

        # pagado
        Estacionamiento.objects.create(
            vehiculo=vehiculo,
            municipio=self.municipio,
            activo=True,
            subcuadra=self.subcuadra,
            registrado_por=self.usuario
        )

        r = verificar_estado_vehiculo("TEST123", self.usuario)
        self.assertEqual(r.estado, EstadoVehiculo.PAGADO)

# =====================================================
# 🚨 INFRACCIONES
# =====================================================

class CrearInfraccionTest(TestCase):

    def setUp(self):
        self.municipio = Municipio.objects.create(nombre="Test")

        self.usuario = Usuario.objects.create(
            email="inspector@test.com",
            es_inspector=True,
            municipio=self.municipio
        )

        self.vehiculo = Vehiculo.objects.create(patente="ABC123")

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
        self.assertEqual(infraccion.vehiculo, self.vehiculo)

    def test_no_permite_exento_total(self):
        self.vehiculo.exento_global = True
        self.vehiculo.save()

        with self.assertRaises(ErrorInfraccion):
            crear_infraccion(
                patente="ABC123",
                subcuadra_id=self.subcuadra.id,
                inspector=self.usuario
            )

    def test_regla_15_min(self):
        Infraccion.objects.create(
            vehiculo=self.vehiculo,
            inspector=self.usuario,
            municipio=self.usuario.municipio,
            subcuadra=self.subcuadra,
        )

        with self.assertRaises(ErrorInfraccion):
            crear_infraccion(
                patente="ABC123",
                subcuadra_id=self.subcuadra.id,
                inspector=self.usuario
            )


# =====================================================
# 🔐 LOGIN
# =====================================================

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
            {"correo": "inspector@test.com", "password": "123456"}
        )

        self.assertRedirects(response, reverse("panel_inspectores"))


# =====================================================
# 🧾 CIERRE DE CAJA
# =====================================================

class CierreCajaTest(TestCase):

    def setUp(self):
        self.inspector = User.objects.create_user(
            correo="inspector@test.com",
            password="123456",
            es_inspector=True,
            saldo_operativo=1000
        )

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
        self.assertEqual(response.url, reverse("panel_inspectores"))

        cierre = CierreCaja.objects.first()

        self.assertIsNotNone(cierre)
        self.assertEqual(cierre.cantidad_movimientos, 1)
        self.assertEqual(cierre.total_cobrado, Decimal("500.00"))