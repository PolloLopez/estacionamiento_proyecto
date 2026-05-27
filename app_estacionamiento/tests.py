# app_estacionamiento/tests.py

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.db.models import Sum
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta

from app_estacionamiento.services_infracciones import crear_infraccion, ErrorInfraccion
from app_estacionamiento.models import Vehiculo, Subcuadra, Infraccion, Usuario, Estacionamiento, MovimientoCaja, Municipio

from app_estacionamiento.services_verificacion import verificar_estado_vehiculo

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

class CajaInspectorTest(TestCase):

    def setUp(self):
        self.inspector = User.objects.create_user(
            correo="inspector@test.com",
            password="123456",
            es_inspector=True,
            saldo_operativo=1000
        )

    def test_calculo_a_rendir(self):
        MovimientoCaja.objects.create(
            usuario=self.inspector,
            monto=Decimal("500"),
            tipo="egreso",
            descripcion="Cobro calle"
        )

        total = MovimientoCaja.objects.filter(
            usuario=self.inspector,
            tipo="egreso"
        ).aggregate(total=Sum("monto"))["total"]

        self.assertEqual(total, Decimal("500"))

    def test_descuenta_saldo_inspector(self):
        self.client.login(correo="inspector@test.com", password="123456")

        self.client.post(
            reverse("inspectores_registrar_estacionamiento_manual"),
            {
                "patente": "TEST123",
                "duracion": "2"
            }
        )

        self.inspector.refresh_from_db()

        self.assertEqual(self.inspector.saldo_operativo, 800)

class VerificacionTest(TestCase):

    def setUp(self):
        # ==============================
        # 🏙 Municipio base
        # ==============================
        self.municipio = Municipio.objects.create(
            nombre="Municipio Test"
        )

        # ==============================
        # 👤 Usuario inspector
        # ==============================
        self.usuario = Usuario.objects.create(
            email="inspector@test.com",
            municipio=self.municipio
        )

    # ==============================
    # 🚫 NO REGISTRADO
    # ==============================
    def test_no_registrado(self):
        resultado = verificar_estado_vehiculo("AAA111", self.usuario)

        self.assertEqual(resultado["estado"], "No registrado (Impago)")
        self.assertFalse(resultado["estacionamiento_activo"])
        self.assertIn("registrar_infraccion_url", resultado)

    # ==============================
    # 🚫 EXENTO TOTAL
    # ==============================
    def test_exento_total(self):
        vehiculo = Vehiculo.objects.create(
            patente="BBB222",
            exento_global=True,
            municipio=self.municipio
        )

        resultado = verificar_estado_vehiculo(vehiculo.patente, self.usuario)

        self.assertEqual(resultado["estado"], "Exento TOTAL")
        self.assertTrue(resultado["estacionamiento_activo"])
        self.assertNotIn("registrar_infraccion_url", resultado)

    # ==============================
    # ❌ IMPAGO
    # ==============================
    def test_impago(self):
        vehiculo = Vehiculo.objects.create(
            patente="CCC333",
            municipio=self.municipio
        )

        resultado = verificar_estado_vehiculo(vehiculo.patente, self.usuario)

        self.assertEqual(resultado["estado"], "Impago")
        self.assertFalse(resultado["estacionamiento_activo"])
        self.assertIn("registrar_infraccion_url", resultado)

    # ==============================
    # ✅ PAGADO
    # ==============================
    def test_pagado(self):
        vehiculo = Vehiculo.objects.create(
        patente="DDD444",
        municipio=self.municipio
    )

        subcuadra = Subcuadra.objects.create(
            calle="Test",
            altura=123,
            municipio=self.municipio
        )

        Estacionamiento.objects.create(
            vehiculo=vehiculo,
            activo=True,
            municipio=self.municipio,
            registrado_por=self.usuario,
            subcuadra=subcuadra
        )

        resultado = verificar_estado_vehiculo(vehiculo.patente, self.usuario)

        self.assertEqual(resultado["estado"], "Pagado")
        self.assertTrue(resultado["estacionamiento_activo"])
        self.assertNotIn("registrar_infraccion_url", resultado)
        
class CrearInfraccionTest(TestCase):

    def setUp(self):
        self.municipio = Municipio.objects.create(nombre="Test")

        self.usuario = Usuario.objects.create(
            email="inspector@test.com",
            es_inspector=True,
            municipio=self.municipio
        )

        self.vehiculo = Vehiculo.objects.create(
            patente="ABC123"
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

        # simular cobro en calle
        MovimientoCaja.objects.create(
            usuario=self.inspector,
            monto=Decimal("300"),
            tipo="egreso",
            descripcion="Cobro prueba"
        )

        response = self.client.post(
            reverse("inspectores_cerrar_caja")
        )

        self.assertEqual(response.status_code, 200)

        from app_estacionamiento.models import CierreCaja

        cierre = CierreCaja.objects.first()

        self.assertIsNotNone(cierre)
        self.assertEqual(cierre.total_cobrado, Decimal("300"))