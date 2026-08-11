# app_estacionamiento/tests_tesorero.py
"""
Tests del flujo tesorero/rendición:
- Acceso al panel tesorero
- Validar / observar rendición
- Admin: crear rendición seleccionando CierreCaja certificados
- Admin: ve sus rendiciones en la página de rendiciones
- Vendedor: ve cierres pendientes de certificación en su panel
"""

from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

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
        """Helper para crear una Rendicion de prueba (totales calculados automáticamente)."""
        hoy = date.today()
        return Rendicion.objects.create(
            municipio=self.municipio,
            admin=self.admin,
            periodo="diario",
            fecha_desde=fecha_desde or hoy - timedelta(days=1),
            fecha_hasta=fecha_hasta or hoy,
            total_efectivo=Decimal("1000"),
            total_digital=Decimal("500"),
            total_neto=Decimal("1500"),
            estado=estado,
        )

    def _crear_cierre(self, usuario, certificado=False, rendicion=None,
                      total_cobrado=Decimal("500"),
                      total_efectivo=Decimal("300"),
                      total_transferencia=Decimal("100"),
                      total_digital=Decimal("100")):
        """Helper para crear un CierreCaja con desglose."""
        return CierreCaja.objects.create(
            usuario=usuario,
            periodo="diario",
            total_cobrado=total_cobrado,
            total_efectivo=total_efectivo,
            total_transferencia=total_transferencia,
            total_digital=total_digital,
            cantidad_movimientos=3,
            certificado=certificado,
            fecha_apertura=timezone.now(),
            rendicion=rendicion,
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
# Admin: crear rendición seleccionando CierreCaja
# ─────────────────────────────────────────────────────────────────────────────

class CrearRendicionTest(BaseTesoreroTest):
    """
    La rendición se genera seleccionando cierres certificados.
    Los totales son calculados por el sistema, no ingresados manualmente.
    """

    def test_get_muestra_cierres_pendientes(self):
        """GET lista cierres certificados y sin rendir."""
        cierre = self._crear_cierre(self.vendedor, certificado=True)
        self.client.force_login(self.admin)

        response = self.client.get(reverse("crear_rendicion"))

        self.assertEqual(response.status_code, 200)
        self.assertIn(cierre, response.context["cierres_pendientes"])

    def test_get_no_muestra_cierres_ya_rendidos(self):
        """Cierres ya vinculados a una rendición no aparecen como disponibles."""
        rendicion = self._crear_rendicion()
        cierre = self._crear_cierre(self.vendedor, certificado=True, rendicion=rendicion)
        self.client.force_login(self.admin)

        response = self.client.get(reverse("crear_rendicion"))

        self.assertNotIn(cierre, response.context["cierres_pendientes"])

    def test_get_no_muestra_cierres_sin_certificar(self):
        """Cierres no certificados no aparecen en la lista."""
        self._crear_cierre(self.vendedor, certificado=False)
        self.client.force_login(self.admin)

        response = self.client.get(reverse("crear_rendicion"))

        self.assertEqual(list(response.context["cierres_pendientes"]), [])

    def test_post_crea_rendicion_con_totales_calculados(self):
        """
        Al enviar cierres seleccionados, la rendición se crea con totales
        calculados automáticamente (efectivo + digital).
        Cierre: efectivo=300, transferencia=100, digital=100 → total_neto=500
        total_digital en Rendicion = 100 (transferencia) + 100 (digital) = 200
        """
        cierre = self._crear_cierre(
            self.vendedor, certificado=True,
            total_efectivo=Decimal("300"),
            total_transferencia=Decimal("100"),
            total_digital=Decimal("100"),
        )
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("crear_rendicion"),
            {"periodo": "diario", "cierre_ids": [cierre.id]},
        )

        self.assertRedirects(response, reverse("admin_rendiciones"))
        rendicion = Rendicion.objects.filter(admin=self.admin).first()
        self.assertIsNotNone(rendicion)
        self.assertEqual(rendicion.total_efectivo, Decimal("300"))
        self.assertEqual(rendicion.total_digital, Decimal("200"))   # 100 + 100
        self.assertEqual(rendicion.total_neto, Decimal("500"))

    def test_post_vincula_cierre_a_rendicion(self):
        """Después de crear la rendición, el cierre tiene FK a ella."""
        cierre = self._crear_cierre(self.vendedor, certificado=True)
        self.client.force_login(self.admin)

        self.client.post(
            reverse("crear_rendicion"),
            {"periodo": "diario", "cierre_ids": [cierre.id]},
        )

        cierre.refresh_from_db()
        self.assertIsNotNone(cierre.rendicion)
        self.assertEqual(cierre.rendicion.admin, self.admin)

    def test_post_sin_cierres_seleccionados_redirige_con_error(self):
        """POST sin cierre_ids seleccionados debe fallar."""
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("crear_rendicion"),
            {"periodo": "diario"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        # No se creó ninguna rendición
        self.assertFalse(Rendicion.objects.filter(admin=self.admin).exists())

    def test_post_no_acepta_cierre_ya_rendido(self):
        """No se puede volver a incluir un cierre que ya está en otra rendición."""
        rendicion_anterior = self._crear_rendicion()
        cierre = self._crear_cierre(
            self.vendedor, certificado=True, rendicion=rendicion_anterior
        )
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("crear_rendicion"),
            {"periodo": "diario", "cierre_ids": [cierre.id]},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        # Solo existe la rendición anterior, no se creó una nueva
        self.assertEqual(Rendicion.objects.count(), 1)

    def test_post_multiples_cierres_suma_totales(self):
        """Con dos cierres seleccionados, los totales se suman correctamente."""
        cierre1 = self._crear_cierre(
            self.vendedor, certificado=True,
            total_efectivo=Decimal("200"),
            total_transferencia=Decimal("50"),
            total_digital=Decimal("0"),
        )
        cierre2 = self._crear_cierre(
            self.admin, certificado=True,
            total_efectivo=Decimal("100"),
            total_transferencia=Decimal("0"),
            total_digital=Decimal("150"),
        )
        self.client.force_login(self.admin)

        self.client.post(
            reverse("crear_rendicion"),
            {"periodo": "mensual", "cierre_ids": [cierre1.id, cierre2.id]},
        )

        rendicion = Rendicion.objects.filter(admin=self.admin).first()
        self.assertEqual(rendicion.total_efectivo, Decimal("300"))    # 200 + 100
        self.assertEqual(rendicion.total_digital, Decimal("200"))     # 50 + 0 + 0 + 150
        self.assertEqual(rendicion.total_neto, Decimal("500"))


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
            total_neto=Decimal("200"),
        )

        self.client.force_login(self.admin)
        response = self.client.get(reverse("admin_rendiciones"))
        self.assertNotIn(rendicion_otra, response.context["mis_rendiciones"])


# ─────────────────────────────────────────────────────────────────────────────
# Vendedor: cierres pendientes en panel
# ─────────────────────────────────────────────────────────────────────────────

class VendedorCierresPendientesTest(BaseTesoreroTest):

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
