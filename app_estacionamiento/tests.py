# app_estacionamiento/tests.py
"""
Tests de los flujos críticos del sistema de estacionamiento.

Correr con:
    python manage.py test app_estacionamiento
"""
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse

from app_estacionamiento.models import (
    Usuario, Municipio, Subcuadra, Vehiculo, VehiculoUsuario,
    Estacionamiento, MovimientoCaja, Tarifa, Infraccion,
)
from app_estacionamiento.services_caja import generar_cierre_caja
from app_estacionamiento.services_infracciones import crear_infraccion, ErrorInfraccion


# ─────────────────────────────────────────────
# Helpers para crear fixtures rápidos
# ─────────────────────────────────────────────

def crear_municipio(nombre="Test"):
    return Municipio.objects.create(nombre=nombre)

def crear_admin(municipio, correo="admin@test.com"):
    return Usuario.objects.create_user(
        correo=correo, password="pass1234",
        municipio=municipio, es_admin=True, es_conductor=False,
    )

def crear_vendedor(municipio, correo="vendedor@test.com", porcentaje=0):
    return Usuario.objects.create_user(
        correo=correo, password="pass1234",
        municipio=municipio, es_vendedor=True, es_conductor=False,
        porcentaje_ganancia=Decimal(str(porcentaje)),
    )

def crear_conductor(municipio, correo="conductor@test.com", saldo=500):
    u = Usuario.objects.create_user(
        correo=correo, password="pass1234",
        municipio=municipio, es_conductor=True,
    )
    u.saldo = Decimal(str(saldo))
    u.save()
    return u

def crear_subcuadra(municipio, calle="San Martín", altura=100):
    return Subcuadra.objects.create(municipio=municipio, calle=calle, altura=altura)

def crear_vehiculo(patente="AAA111"):
    return Vehiculo.objects.create(patente=patente)

def crear_estacionamiento_activo(usuario, vehiculo, subcuadra, duracion=2, costo=200):
    return Estacionamiento.objects.create(
        usuario=usuario, vehiculo=vehiculo, subcuadra=subcuadra,
        duracion_min=duracion, costo_base=costo, estado="ACTIVO",
    )


# ═════════════════════════════════════════════
# 1. SERVICIO: generar_cierre_caja
# ═════════════════════════════════════════════

class TestGenerarCierreCaja(TestCase):

    def setUp(self):
        self.municipio = crear_municipio()
        self.vendedor  = crear_vendedor(self.municipio, porcentaje=10)

    def _crear_movimientos(self, montos):
        for m in montos:
            MovimientoCaja.objects.create(
                usuario=self.vendedor, monto=Decimal(str(m)), tipo="ingreso"
            )

    def test_cierre_sin_movimientos_retorna_none(self):
        resultado = generar_cierre_caja(self.vendedor)
        self.assertIsNone(resultado)

    def test_cierre_suma_movimientos(self):
        self._crear_movimientos([100, 200, 300])
        cierre = generar_cierre_caja(self.vendedor)
        self.assertEqual(cierre.total_cobrado, Decimal("600"))

    def test_cierre_aplica_comision(self):
        """Con 10% de comisión sobre $1000: ganancia=$100, municipio=$900."""
        self._crear_movimientos([1000])
        cierre = generar_cierre_caja(self.vendedor)
        self.assertEqual(cierre.porcentaje_ganancia_aplicado, Decimal("10"))
        self.assertEqual(cierre.ganancia_usuario, Decimal("100.00"))
        self.assertEqual(cierre.monto_municipio, Decimal("900.00"))

    def test_cierre_sin_comision(self):
        """Con 0% el municipio recibe el total."""
        vendedor_sin_comision = crear_vendedor(
            self.municipio, correo="v2@test.com", porcentaje=0
        )
        MovimientoCaja.objects.create(
            usuario=vendedor_sin_comision, monto=Decimal("500"), tipo="ingreso"
        )
        cierre = generar_cierre_caja(vendedor_sin_comision)
        self.assertEqual(cierre.ganancia_usuario, Decimal("0.00"))
        self.assertEqual(cierre.monto_municipio, Decimal("500.00"))

    def test_cierre_marca_movimientos_cerrados(self):
        """Los movimientos deben quedar cerrado=True después del cierre."""
        self._crear_movimientos([100, 200])
        generar_cierre_caja(self.vendedor)
        abiertos = MovimientoCaja.objects.filter(usuario=self.vendedor, cerrado=False)
        self.assertEqual(abiertos.count(), 0)

    def test_segundo_cierre_sin_movimientos_retorna_none(self):
        """Después de cerrar, sin nuevos movimientos el cierre retorna None."""
        self._crear_movimientos([100])
        generar_cierre_caja(self.vendedor)
        self.assertIsNone(generar_cierre_caja(self.vendedor))


# ═════════════════════════════════════════════
# 2. SEGURIDAD: aislamiento de municipio
# ═════════════════════════════════════════════

class TestAislamientoMunicipio(TestCase):
    """Admin de municipio A NO puede acceder a datos de municipio B."""

    def setUp(self):
        self.municipio_a  = crear_municipio("Municipio A")
        self.municipio_b  = crear_municipio("Municipio B")
        self.admin_a      = crear_admin(self.municipio_a, "admin_a@test.com")
        self.conductor_b  = crear_conductor(self.municipio_b, "conductor_b@test.com")
        self.client = Client()
        self.client.force_login(self.admin_a)

    def test_cargar_saldo_otro_municipio_retorna_404(self):
        url = reverse("cargar_saldo", args=[self.conductor_b.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_detalle_usuario_otro_municipio_retorna_404(self):
        url = reverse("detalle_usuario_admin", args=[self.conductor_b.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_editar_vendedor_otro_municipio_retorna_404(self):
        vendedor_b = crear_vendedor(self.municipio_b, "vendedor_b@test.com")
        url = reverse("admin_editar_vendedor", args=[vendedor_b.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_certificar_cierre_otro_municipio_retorna_404(self):
        vendedor_b = crear_vendedor(self.municipio_b, "v_b@test.com")
        MovimientoCaja.objects.create(
            usuario=vendedor_b, monto=Decimal("100"), tipo="ingreso"
        )
        cierre = generar_cierre_caja(vendedor_b)
        url = reverse("certificar_cierre", args=[cierre.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 404)


# ═════════════════════════════════════════════
# 3. RENOVAR ESTACIONAMIENTO
# ═════════════════════════════════════════════

class TestRenovarEstacionamiento(TestCase):

    def setUp(self):
        self.municipio = crear_municipio()
        self.conductor = crear_conductor(self.municipio, saldo=500)
        self.vehiculo  = crear_vehiculo("BBB222")
        VehiculoUsuario.objects.create(usuario=self.conductor, vehiculo=self.vehiculo)
        self.subcuadra = crear_subcuadra(self.municipio)
        Tarifa.objects.create(municipio=self.municipio, precio_por_hora=Decimal("100"))
        self.est = crear_estacionamiento_activo(
            self.conductor, self.vehiculo, self.subcuadra, duracion=2, costo=200
        )
        self.client = Client()
        self.client.force_login(self.conductor)
        self.url = reverse("usuarios_renovar_estacionamiento", args=[self.est.id])

    def test_renovar_extiende_duracion(self):
        self.client.post(self.url, {"horas_extra": "2"})
        self.est.refresh_from_db()
        self.assertEqual(self.est.duracion_min, 4)  # 2 originales + 2 extra

    def test_renovar_descuenta_saldo(self):
        self.client.post(self.url, {"horas_extra": "1"})
        self.conductor.refresh_from_db()
        # $100/h × 1h = $100 descontado de $500
        self.assertEqual(self.conductor.saldo, Decimal("400"))

    def test_renovar_sin_saldo_no_modifica(self):
        """Con saldo insuficiente no cambia ni duración ni saldo."""
        self.conductor.saldo = Decimal("50")
        self.conductor.save()
        self.client.post(self.url, {"horas_extra": "2"})  # costaría $200
        self.est.refresh_from_db()
        self.conductor.refresh_from_db()
        self.assertEqual(self.est.duracion_min, 2)
        self.assertEqual(self.conductor.saldo, Decimal("50"))

    def test_renovar_estacionamiento_ajeno_retorna_404(self):
        """No puede renovar un estacionamiento de otro conductor."""
        otro = crear_conductor(self.municipio, "otro@test.com", saldo=500)
        client2 = Client()
        client2.force_login(otro)
        response = client2.post(self.url, {"horas_extra": "1"})
        self.assertEqual(response.status_code, 404)


# ═════════════════════════════════════════════
# 4. ACCESO POR ROL
# ═════════════════════════════════════════════

class TestAccesoRol(TestCase):
    """Verifica que @require_role redirige correctamente."""

    def setUp(self):
        self.municipio = crear_municipio()
        self.conductor = crear_conductor(self.municipio)
        self.client = Client()

    def test_conductor_no_accede_panel_admin(self):
        self.client.force_login(self.conductor)
        response = self.client.get(reverse("panel_admin"))
        self.assertNotEqual(response.status_code, 200)

    def test_conductor_no_accede_panel_inspectores(self):
        self.client.force_login(self.conductor)
        response = self.client.get(reverse("panel_inspectores"))
        self.assertNotEqual(response.status_code, 200)

    def test_anonimo_redirige_a_login(self):
        response = self.client.get(reverse("inicio_usuarios"))
        self.assertIn(response.status_code, [301, 302])

    def test_admin_accede_panel_admin(self):
        admin = crear_admin(self.municipio)
        self.client.force_login(admin)
        response = self.client.get(reverse("panel_admin"))
        self.assertEqual(response.status_code, 200)


# ═════════════════════════════════════════════
# 5. ALTA INSPECTOR / VENDEDOR
# ═════════════════════════════════════════════

class TestAltaPersonal(TestCase):
    """Al crear inspector/vendedor se guarda porcentaje y periodicidad."""

    def setUp(self):
        self.municipio = crear_municipio()
        self.admin = crear_admin(self.municipio)
        self.client = Client()
        self.client.force_login(self.admin)

    def test_crear_inspector_con_comision(self):
        self.client.post(reverse("admin_crear_inspector"), {
            "nombre": "Juan Inspector",
            "correo": "inspector_nuevo@test.com",
            "password": "pass1234",
            "porcentaje_ganancia": "15",
            "periodicidad_rendicion": "mensual",
        })
        inspector = Usuario.objects.get(correo="inspector_nuevo@test.com")
        self.assertEqual(inspector.porcentaje_ganancia, Decimal("15"))
        self.assertEqual(inspector.periodicidad_rendicion, "mensual")

    def test_crear_vendedor_con_comision(self):
        self.client.post(reverse("admin_crear_vendedor"), {
            "nombre": "Kiosco Sur",
            "correo": "vendedor_nuevo@test.com",
            "password": "pass1234",
            "porcentaje_ganancia": "8",
            "periodicidad_rendicion": "semanal",
        })
        vendedor = Usuario.objects.get(correo="vendedor_nuevo@test.com")
        self.assertEqual(vendedor.porcentaje_ganancia, Decimal("8"))
        self.assertEqual(vendedor.periodicidad_rendicion, "semanal")


# ═════════════════════════════════════════════
# 6. MONTO DE INFRACCIÓN DESDE TARIFA
# ═════════════════════════════════════════════

class TestMontoInfraccion(TestCase):
    """
    El monto de cada infracción debe tomarse de Tarifa.monto_infraccion
    configurada por el admin, no quedar en $0.
    """

    def setUp(self):
        self.municipio = crear_municipio()
        self.inspector = Usuario.objects.create_user(
            correo="inspector@test.com", password="pass1234",
            municipio=self.municipio, es_inspector=True, es_conductor=False,
        )
        self.subcuadra = crear_subcuadra(self.municipio)
        self.vehiculo  = crear_vehiculo("ZZZ999")

    def test_infraccion_toma_monto_de_tarifa(self):
        """Si la tarifa tiene monto_infraccion=3000, la infracción se crea con $3000."""
        Tarifa.objects.create(
            municipio=self.municipio,
            precio_por_hora=Decimal("100"),
            monto_infraccion=Decimal("3000"),
        )
        infraccion = crear_infraccion(
            patente=self.vehiculo.patente,
            subcuadra_id=self.subcuadra.id,
            inspector=self.inspector,
        )
        self.assertEqual(infraccion.monto, Decimal("3000"))

    def test_infraccion_sin_tarifa_monto_cero(self):
        """Sin tarifa configurada el monto queda en $0 (estado seguro)."""
        infraccion = crear_infraccion(
            patente=self.vehiculo.patente,
            subcuadra_id=self.subcuadra.id,
            inspector=self.inspector,
        )
        self.assertEqual(infraccion.monto, Decimal("0"))

    def test_infraccion_monto_no_depende_de_precio_hora(self):
        """El precio/hora NO afecta el monto de infracción — son campos independientes."""
        Tarifa.objects.create(
            municipio=self.municipio,
            precio_por_hora=Decimal("500"),   # precio alto de estacionamiento
            monto_infraccion=Decimal("1500"),  # infracción separada
        )
        infraccion = crear_infraccion(
            patente=self.vehiculo.patente,
            subcuadra_id=self.subcuadra.id,
            inspector=self.inspector,
        )
        self.assertEqual(infraccion.monto, Decimal("1500"))

    def test_admin_actualiza_monto_infraccion(self):
        """POST a gestionar_tarifas guarda monto_infraccion correctamente."""
        admin = crear_admin(self.municipio)
        client = Client()
        client.force_login(admin)
        client.post(reverse("admin_guardar_tarifa"), {
            "precio_por_hora": "200",
            "monto_infraccion": "4500",
        })
        tarifa = Tarifa.objects.get(municipio=self.municipio)
        self.assertEqual(tarifa.monto_infraccion, Decimal("4500"))
        self.assertEqual(tarifa.precio_por_hora, Decimal("200"))
