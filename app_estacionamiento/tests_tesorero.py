# app_estacionamiento/tests_tesorero.py
"""
Tests del flujo tesorero:
- Acceso al panel
- Validar / observar rendición
- Admin: fecha_desde sugerida al crear rendición
- Admin: ve sus rendiciones en la página de rendiciones
- Vendedor: ve cierres pendientes de certificación en su panel
"""

from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from app_estacionamiento.models import (
    CierreCaja,
    Municipio,
    Rendicion,
    Tarifa,
    Usuario,
)


class BaseTesoreroTest(TestCase):
    """Datos comunes para todos los tests de tesorero."""

    def setUp(self):
        self.municipio = Municipio.objects.create(nombre="TestMunicipio")

        Tarifa.objects.create(
            municipio=self.municipio,
            precio_por_hora=Decimal("100"),
        )

        self.admin = Usuario.objects.create_user(
            correo="admin@test.com", password="123",
            municipio=self.municipio, es_admin=True, es_conductor=False,
        )
        self.tesorero = Usuario.objects.create_user(
            correo="tesorero@test.com", password="123",
            municipio=self.municipio, es_tesorero=True, es_conductor=False,
        )
        self.vendedor = Usuario.objects.create_user(
            correo="vendedor@test.com", password="123",
            municipio=self.municipio, es_vendedor=True, es_conductor=False,
        )
        self.conductor = Usuario.objects.create_user(
            correo="conductor@test.com", password="123",
            municipio=self.municipio, es_conductor=True,
            first_name="Test",  # evita redirección del middleware (conductor sin nombre)
        )

    def _crear_rendicion(self, fecha_desde=None, fecha_hasta=None, estado="pendiente"):
        """Helper para crear una Rendicion de prueba."""
        hoy = date.today()
        return Rendicion.objects.create(
            municipio=self.municipio,
            admin=self.admin,
            periodo="diario",
            fecha_desde=fecha_desde or hoy - timedelta(days=1),
            fecha_hasta=fecha_hasta or hoy,
            total_efectivo=Decimal("1000"),
            total_digital=Decimal("500"),
            total_comisiones=Decimal("100"),
            total_neto=Decimal("1400"),
            estado=estado,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Acceso al panel tesorero
# ─────────────────────────────────────────────────────────────────────────────

class AccesoPanelTesoreroTest(BaseTesoreroTest):

    def test_tesorero_puede_ver_panel(self):
        self.client.force_login(self.tesorero)
        response = self.client.get(reverse("panel_tesorero"))
        self.assertEqual(response.status_code, 200)

    def test_conductor_no_puede_ver_panel_tesorero(self):
        self.client.force_login(self.conductor)
        response = self.client.get(reverse("panel_tesorero"))
        self.assertEqual(response.status_code, 403)

    def test_admin_no_puede_ver_panel_tesorero(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("panel_tesorero"))
        self.assertEqual(response.status_code, 403)

    def test_anonimo_redirige_a_login(self):
        response = self.client.get(reverse("panel_tesorero"))
        self.assertRedirects(response, reverse("login"))


# ─────────────────────────────────────────────────────────────────────────────
# Validar rendición
# ─────────────────────────────────────────────────────────────────────────────

class ValidarRendicionTest(BaseTesoreroTest):

    def test_tesorero_valida_rendicion(self):
        rendicion = self._crear_rendicion()
        self.client.force_login(self.tesorero)

        response = self.client.post(
            reverse("validar_rendicion", args=[rendicion.id]),
            {"accion": "validar", "notas_tesorero": "OK"},
        )

        self.assertRedirects(response, reverse("panel_tesorero"))
        rendicion.refresh_from_db()
        self.assertEqual(rendicion.estado, "validada")
        self.assertEqual(rendicion.tesorero, self.tesorero)
        self.assertIsNotNone(rendicion.validado_en)
        self.assertEqual(rendicion.notas_tesorero, "OK")

    def test_tesorero_observa_rendicion(self):
        rendicion = self._crear_rendicion()
        self.client.force_login(self.tesorero)

        self.client.post(
            reverse("validar_rendicion", args=[rendicion.id]),
            {"accion": "observar", "notas_tesorero": "Falta documentación"},
        )

        rendicion.refresh_from_db()
        self.assertEqual(rendicion.estado, "observada")
        self.assertEqual(rendicion.notas_tesorero, "Falta documentación")

    def test_no_puede_validar_rendicion_ya_procesada(self):
        """Una rendición ya validada no cambia de estado."""
        rendicion = self._crear_rendicion(estado="validada")
        self.client.force_login(self.tesorero)

        self.client.post(
            reverse("validar_rendicion", args=[rendicion.id]),
            {"accion": "validar"},
        )

        rendicion.refresh_from_db()
        # Sigue en "validada", no cambia a otro estado
        self.assertEqual(rendicion.estado, "validada")

    def test_conductor_no_puede_validar_rendicion(self):
        rendicion = self._crear_rendicion()
        self.client.force_login(self.conductor)

        response = self.client.post(
            reverse("validar_rendicion", args=[rendicion.id]),
            {"accion": "validar"},
        )

        self.assertEqual(response.status_code, 403)
        rendicion.refresh_from_db()
        self.assertEqual(rendicion.estado, "pendiente")  # no cambió

    def test_get_a_validar_redirige_sin_cambiar_estado(self):
        """GET no debe validar nada, solo redirige al panel."""
        rendicion = self._crear_rendicion()
        self.client.force_login(self.tesorero)

        self.client.get(reverse("validar_rendicion", args=[rendicion.id]))

        rendicion.refresh_from_db()
        self.assertEqual(rendicion.estado, "pendiente")


# ─────────────────────────────────────────────────────────────────────────────
# Admin: fecha_desde sugerida al crear rendición
# ─────────────────────────────────────────────────────────────────────────────

class CrearRendicionFechaDesdeTest(BaseTesoreroTest):

    def test_sin_rendiciones_previas_sugiere_primer_dia_del_mes(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("crear_rendicion"))
        self.assertEqual(response.status_code, 200)
        fecha_sugerida = response.context["fecha_desde_sugerida"]
        self.assertEqual(fecha_sugerida.day, 1)

    def test_con_rendicion_previa_sugiere_dia_siguiente(self):
        fecha_hasta_anterior = date.today() - timedelta(days=3)
        self._crear_rendicion(
            fecha_desde=fecha_hasta_anterior - timedelta(days=6),
            fecha_hasta=fecha_hasta_anterior,
        )

        self.client.force_login(self.admin)
        response = self.client.get(reverse("crear_rendicion"))
        self.assertEqual(response.status_code, 200)

        fecha_sugerida = response.context["fecha_desde_sugerida"]
        self.assertEqual(fecha_sugerida, fecha_hasta_anterior + timedelta(days=1))

    def test_multiples_rendiciones_usa_la_mas_reciente(self):
        """Con varias rendiciones, toma la de fecha_hasta más reciente."""
        hoy = date.today()
        self._crear_rendicion(
            fecha_desde=hoy - timedelta(days=14),
            fecha_hasta=hoy - timedelta(days=8),
        )
        rendicion_reciente = self._crear_rendicion(
            fecha_desde=hoy - timedelta(days=7),
            fecha_hasta=hoy - timedelta(days=1),
        )

        self.client.force_login(self.admin)
        response = self.client.get(reverse("crear_rendicion"))
        fecha_sugerida = response.context["fecha_desde_sugerida"]
        self.assertEqual(fecha_sugerida, rendicion_reciente.fecha_hasta + timedelta(days=1))


# ─────────────────────────────────────────────────────────────────────────────
# Admin: ve sus propias rendiciones en la página de rendiciones
# ─────────────────────────────────────────────────────────────────────────────

class MisRendicionesAdminTest(BaseTesoreroTest):

    def test_admin_ve_sus_rendiciones_en_pagina(self):
        rendicion = self._crear_rendicion()
        self.client.force_login(self.admin)

        response = self.client.get(reverse("admin_rendiciones"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(rendicion, response.context["mis_rendiciones"])

    def test_rendicion_de_otro_admin_no_aparece(self):
        otro_admin = Usuario.objects.create_user(
            correo="otro@test.com", password="123",
            municipio=self.municipio, es_admin=True, es_conductor=False,
        )
        rendicion_otra = Rendicion.objects.create(
            municipio=self.municipio,
            admin=otro_admin,
            periodo="diario",
            fecha_desde=date.today() - timedelta(days=1),
            fecha_hasta=date.today(),
            total_efectivo=Decimal("200"),
            total_digital=Decimal("0"),
            total_comisiones=Decimal("0"),
            total_neto=Decimal("200"),
        )

        self.client.force_login(self.admin)
        response = self.client.get(reverse("admin_rendiciones"))
        self.assertNotIn(rendicion_otra, response.context["mis_rendiciones"])


# ─────────────────────────────────────────────────────────────────────────────
# Vendedor: cierres pendientes en panel
# ─────────────────────────────────────────────────────────────────────────────

class VendedorCierresPendientesTest(BaseTesoreroTest):

    def _crear_cierre(self, usuario, certificado=False):
        from django.utils import timezone
        return CierreCaja.objects.create(
            usuario=usuario,
            periodo="diario",
            total_cobrado=Decimal("500"),
            cantidad_movimientos=3,
            certificado=certificado,
            fecha_apertura=timezone.now(),
        )

    def test_panel_vendedor_muestra_cierres_sin_certificar(self):
        cierre = self._crear_cierre(self.vendedor, certificado=False)
        self.client.force_login(self.vendedor)

        response = self.client.get(reverse("panel_vendedor"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(cierre, response.context["cierres_sin_certificar"])

    def test_cierre_certificado_no_aparece_como_pendiente(self):
        self._crear_cierre(self.vendedor, certificado=True)
        self.client.force_login(self.vendedor)

        response = self.client.get(reverse("panel_vendedor"))
        pendientes = list(response.context["cierres_sin_certificar"])
        self.assertEqual(len(pendientes), 0)

    def test_cierre_de_otro_vendedor_no_aparece(self):
        otro_vendedor = Usuario.objects.create_user(
            correo="otro_vendedor@test.com", password="123",
            municipio=self.municipio, es_vendedor=True, es_conductor=False,
        )
        self._crear_cierre(otro_vendedor, certificado=False)
        self.client.force_login(self.vendedor)

        response = self.client.get(reverse("panel_vendedor"))
        pendientes = list(response.context["cierres_sin_certificar"])
        self.assertEqual(len(pendientes), 0)
