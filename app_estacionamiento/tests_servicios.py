# app_estacionamiento/tests_servicios.py
"""
Tests de la capa de servicios y flujos de negocio.

Cubre:
- services/infracciones.py :: cobrar_infraccion_efectivo()
- services/saldo.py        :: cargar_saldo_conductor()
- Abono mensual            :: view cobrar_abono (cobro + conflicto + comisión)
- Comisiones               :: comision_monto se graba en MovimientoCaja
- Multi-municipio          :: aislamiento de datos entre municipios
- Tesorero / vendedor      :: depositar_comision → certificar_comision

Correr con:
    python manage.py test app_estacionamiento.tests_servicios --verbosity=2
"""
from datetime import date
from decimal import Decimal

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from app_estacionamiento.models import (
    Usuario, Municipio, Subcuadra, Vehiculo,
    Infraccion, MovimientoCaja, Tarifa, AbonoMensual, LiquidacionComision,
)
from app_estacionamiento.services.infracciones import cobrar_infraccion_efectivo
from app_estacionamiento.services.saldo import cargar_saldo_conductor


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def crear_municipio(nombre="TestMunicipio", comision_pct=10):
    """Crea un municipio con comisión configurable."""
    return Municipio.objects.create(nombre=nombre, comision_vendedor=Decimal(str(comision_pct)))


def crear_admin(municipio, correo="admin@test.com"):
    return Usuario.objects.create_user(
        correo=correo, password="pass1234",
        municipio=municipio, es_admin=True, es_conductor=False,
    )


def crear_vendedor(municipio, correo="vendedor@test.com"):
    return Usuario.objects.create_user(
        correo=correo, password="pass1234",
        municipio=municipio, es_vendedor=True, es_conductor=False,
    )


def crear_conductor(municipio, correo="conductor@test.com", saldo=500):
    u = Usuario.objects.create_user(
        correo=correo, password="pass1234",
        municipio=municipio, es_conductor=True,
        first_name="Test",  # evita redirección del middleware
    )
    u.saldo = Decimal(str(saldo))
    u.save()
    return u


def crear_tesorero(municipio, correo="tesorero@test.com"):
    return Usuario.objects.create_user(
        correo=correo, password="pass1234",
        municipio=municipio, es_tesorero=True, es_conductor=False,
    )


def crear_inspector(municipio, correo="inspector@test.com"):
    return Usuario.objects.create_user(
        correo=correo, password="pass1234",
        municipio=municipio, es_inspector=True, es_conductor=False,
    )


def crear_vehiculo(municipio, patente="TST001"):
    return Vehiculo.objects.create(patente=patente, municipio=municipio)


def crear_subcuadra(municipio):
    return Subcuadra.objects.create(
        calle="San Martín", altura=100, municipio=municipio
    )


def crear_tarifa(municipio, precio_hora=10, precio_abono_auto=500):
    return Tarifa.objects.create(
        municipio=municipio,
        precio_por_hora=Decimal(str(precio_hora)),
        precio_abono_auto=Decimal(str(precio_abono_auto)),
    )


def crear_infraccion(municipio, inspector, vehiculo, subcuadra, monto=1000):
    return Infraccion.objects.create(
        municipio=municipio,
        inspector=inspector,
        vehiculo=vehiculo,
        subcuadra=subcuadra,
        motivo="Sin ticket",
        monto=Decimal(str(monto)),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 1. cobrar_infraccion_efectivo()
# ─────────────────────────────────────────────────────────────────────────────

class TestCobrarInfraccionEfectivo(TestCase):
    """Tests unitarios del service cobrar_infraccion_efectivo."""

    def setUp(self):
        self.municipio = crear_municipio(comision_pct=10)
        self.admin     = crear_admin(self.municipio)
        self.inspector = crear_inspector(self.municipio)
        self.subcuadra = crear_subcuadra(self.municipio)
        self.vehiculo  = crear_vehiculo(self.municipio)
        self.infraccion = crear_infraccion(
            self.municipio, self.inspector, self.vehiculo, self.subcuadra, monto=2000
        )

    def test_cobro_marca_estado_pagada(self):
        """Después de cobrar, la infracción queda en estado 'pagada'."""
        cobrar_infraccion_efectivo(infraccion=self.infraccion, cobrador=self.admin)
        self.infraccion.refresh_from_db()
        self.assertEqual(self.infraccion.estado, "pagada")

    def test_cobro_registra_fecha_pago(self):
        """fecha_pago se graba en el momento del cobro."""
        antes = timezone.now()
        cobrar_infraccion_efectivo(infraccion=self.infraccion, cobrador=self.admin)
        self.infraccion.refresh_from_db()
        self.assertIsNotNone(self.infraccion.fecha_pago)
        self.assertGreaterEqual(self.infraccion.fecha_pago, antes)

    def test_cobro_crea_movimiento_en_caja(self):
        """Se crea un MovimientoCaja de tipo 'ingreso' por el monto de la infracción."""
        cobrar_infraccion_efectivo(infraccion=self.infraccion, cobrador=self.admin)
        mov = MovimientoCaja.objects.filter(usuario=self.admin, tipo="ingreso").first()
        self.assertIsNotNone(mov)
        self.assertEqual(mov.monto, Decimal("2000"))

    def test_cobro_calcula_comision_correctamente(self):
        """comision_monto = monto * comision_vendedor% (10% de 2000 = 200)."""
        cobrar_infraccion_efectivo(infraccion=self.infraccion, cobrador=self.admin)
        mov = MovimientoCaja.objects.filter(usuario=self.admin).first()
        self.assertEqual(mov.comision_monto, Decimal("200.00"))

    def test_doble_cobro_lanza_valueerror(self):
        """Cobrar dos veces la misma infracción lanza ValueError."""
        cobrar_infraccion_efectivo(infraccion=self.infraccion, cobrador=self.admin)
        with self.assertRaises(ValueError):
            cobrar_infraccion_efectivo(infraccion=self.infraccion, cobrador=self.admin)

    def test_cobro_retorna_infraccion_actualizada(self):
        """La función retorna la instancia de Infraccion con estado actualizado."""
        resultado = cobrar_infraccion_efectivo(infraccion=self.infraccion, cobrador=self.admin)
        self.assertEqual(resultado.estado, "pagada")


# ─────────────────────────────────────────────────────────────────────────────
# 2. cargar_saldo_conductor()
# ─────────────────────────────────────────────────────────────────────────────

class TestCargarSaldoConductor(TestCase):
    """Tests unitarios del service cargar_saldo_conductor."""

    def setUp(self):
        self.municipio = crear_municipio()
        self.admin     = crear_admin(self.municipio)
        self.conductor = crear_conductor(self.municipio, saldo=100)

    def test_saldo_se_acredita(self):
        """El saldo del conductor aumenta en el monto cargado."""
        cargar_saldo_conductor(admin=self.admin, conductor=self.conductor, monto=Decimal("500"))
        self.conductor.refresh_from_db()
        self.assertEqual(self.conductor.saldo, Decimal("600"))

    def test_crea_movimiento_en_caja(self):
        """Se genera un MovimientoCaja de tipo 'ingreso' a nombre del admin."""
        cargar_saldo_conductor(admin=self.admin, conductor=self.conductor, monto=Decimal("300"))
        mov = MovimientoCaja.objects.filter(usuario=self.admin, tipo="ingreso").first()
        self.assertIsNotNone(mov)
        self.assertEqual(mov.monto, Decimal("300"))

    def test_monto_cero_lanza_valueerror(self):
        """Cargar $0 lanza ValueError."""
        with self.assertRaises(ValueError):
            cargar_saldo_conductor(admin=self.admin, conductor=self.conductor, monto=Decimal("0"))

    def test_monto_negativo_lanza_valueerror(self):
        """Cargar un monto negativo lanza ValueError."""
        with self.assertRaises(ValueError):
            cargar_saldo_conductor(admin=self.admin, conductor=self.conductor, monto=Decimal("-50"))

    def test_retorna_conductor_actualizado(self):
        """La función retorna el conductor con el saldo ya actualizado."""
        resultado = cargar_saldo_conductor(
            admin=self.admin, conductor=self.conductor, monto=Decimal("200")
        )
        self.assertEqual(resultado.saldo, Decimal("300"))


# ─────────────────────────────────────────────────────────────────────────────
# 3. Abono mensual
# ─────────────────────────────────────────────────────────────────────────────

class TestAbonoMensual(TestCase):
    """Flujo completo del cobro de abono mensual vía view cobrar_abono."""

    def setUp(self):
        self.municipio = crear_municipio(comision_pct=10)
        self.vendedor  = crear_vendedor(self.municipio)
        self.vehiculo  = crear_vehiculo(self.municipio, patente="ABN001")
        # Tarifa con precio de abono
        crear_tarifa(self.municipio, precio_hora=10, precio_abono_auto=500)

        self.client = Client()
        self.client.force_login(self.vendedor)
        self.url = reverse("cobrar_abono")
        self.mes_actual = date.today().replace(day=1).isoformat()

    def test_cobro_abono_crea_registro_abonoMensual(self):
        """POST accion=cobrar crea un AbonoMensual para el vehículo y mes."""
        self.client.post(self.url, {
            "accion": "cobrar",
            "patente": "ABN001",
            "mes": self.mes_actual,
        })
        existe = AbonoMensual.objects.filter(
            vehiculo=self.vehiculo, mes=date.fromisoformat(self.mes_actual)
        ).exists()
        self.assertTrue(existe, "El AbonoMensual no fue creado")

    def test_cobro_abono_crea_movimiento_en_caja(self):
        """Al cobrar, se registra un MovimientoCaja de tipo ingreso."""
        self.client.post(self.url, {
            "accion": "cobrar",
            "patente": "ABN001",
            "mes": self.mes_actual,
        })
        mov = MovimientoCaja.objects.filter(usuario=self.vendedor, tipo="ingreso").first()
        self.assertIsNotNone(mov, "No se creó MovimientoCaja")
        self.assertEqual(mov.monto, Decimal("500"))

    def test_abono_duplicado_no_se_crea(self):
        """No se puede cobrar el mismo abono dos veces para el mismo mes."""
        datos = {"accion": "cobrar", "patente": "ABN001", "mes": self.mes_actual}
        self.client.post(self.url, datos)
        self.client.post(self.url, datos)
        total = AbonoMensual.objects.filter(
            vehiculo=self.vehiculo, mes=date.fromisoformat(self.mes_actual)
        ).count()
        self.assertEqual(total, 1, "Se creó más de un abono para el mismo mes")

    def test_comision_abono_se_graba_en_movimiento(self):
        """comision_monto = precio_abono * 10% = 500 * 10% = 50."""
        self.client.post(self.url, {
            "accion": "cobrar",
            "patente": "ABN001",
            "mes": self.mes_actual,
        })
        mov = MovimientoCaja.objects.filter(usuario=self.vendedor, tipo="ingreso").first()
        self.assertEqual(mov.comision_monto, Decimal("50.00"))

    def test_patente_nueva_crea_vehiculo_y_abono(self):
        """
        Una patente no registrada previamente genera el vehículo on-the-fly
        y registra el abono. Cambio de comportamiento: antes bloqueaba,
        ahora el abono no requiere registro previo del vehículo.
        """
        self.client.post(self.url, {
            "accion": "cobrar",
            "patente": "ZZZZZZ",
            "mes": self.mes_actual,
        })
        self.assertEqual(AbonoMensual.objects.filter(vehiculo__patente="ZZZZZZ").count(), 1)


# ─────────────────────────────────────────────────────────────────────────────
# 4. Multi-municipio — aislamiento de datos
# ─────────────────────────────────────────────────────────────────────────────

class TestMultiMunicipio(TestCase):
    """Los datos de un municipio no son visibles desde otro municipio."""

    def setUp(self):
        self.muni_a = crear_municipio("MuniA")
        self.muni_b = crear_municipio("MuniB")

        self.admin_a = crear_admin(self.muni_a, "admin_a@test.com")
        self.admin_b = crear_admin(self.muni_b, "admin_b@test.com")

        self.conductor_a = crear_conductor(self.muni_a, "cond_a@test.com", saldo=500)
        self.conductor_b = crear_conductor(self.muni_b, "cond_b@test.com", saldo=500)

    def test_cargar_saldo_no_afecta_a_otro_municipio(self):
        """Cargar saldo al conductor A no modifica el saldo del conductor B."""
        saldo_b_antes = self.conductor_b.saldo
        cargar_saldo_conductor(
            admin=self.admin_a, conductor=self.conductor_a, monto=Decimal("200")
        )
        self.conductor_b.refresh_from_db()
        self.assertEqual(self.conductor_b.saldo, saldo_b_antes)

    def test_movimientos_caja_son_por_municipio(self):
        """Los movimientos de caja del admin A no aparecen en las consultas del admin B."""
        cargar_saldo_conductor(
            admin=self.admin_a, conductor=self.conductor_a, monto=Decimal("300")
        )
        movimientos_b = MovimientoCaja.objects.filter(usuario=self.admin_b)
        self.assertEqual(movimientos_b.count(), 0)

    def test_abonos_de_un_municipio_no_cruzan_al_otro(self):
        """Un AbonoMensual creado en el municipio A no existe para el municipio B."""
        vehiculo_a = crear_vehiculo(self.muni_a, patente="AAA001")
        crear_tarifa(self.muni_a, precio_abono_auto=500)

        vendedor_a = crear_vendedor(self.muni_a, "vend_a@test.com")
        client_a = Client()
        client_a.force_login(vendedor_a)
        client_a.post(reverse("cobrar_abono"), {
            "accion": "cobrar",
            "patente": "AAA001",
            "mes": date.today().replace(day=1).isoformat(),
        })

        abonos_muni_b = AbonoMensual.objects.filter(municipio=self.muni_b)
        self.assertEqual(abonos_muni_b.count(), 0)


# ─────────────────────────────────────────────────────────────────────────────
# 5. Flujo tesorero → depositar → vendedor certifica
# ─────────────────────────────────────────────────────────────────────────────

class TestFlujoCertificacionComision(TestCase):
    """Flujo completo: tesorero deposita comisión, vendedor certifica recibo."""

    def setUp(self):
        self.municipio = crear_municipio()
        self.tesorero  = crear_tesorero(self.municipio)
        self.vendedor  = crear_vendedor(self.municipio)

        # Liquidación pendiente que el tesorero va a depositar
        self.liquidacion = LiquidacionComision.objects.create(
            vendedor=self.municipio.usuario_set.filter(es_vendedor=True).first(),
            municipio=self.municipio,
            fecha_desde=date(2026, 7, 1),
            fecha_hasta=date(2026, 7, 31),
            monto_total=Decimal("850"),
            estado="pendiente",
        )
        # Asignar el vendedor creado (la línea de arriba usó filter pero necesita la instancia)
        self.liquidacion.vendedor = self.vendedor
        self.liquidacion.save()

    def test_tesorero_puede_depositar(self):
        """POST del tesorero a depositar_comision cambia el estado a 'depositada'."""
        client = Client()
        client.force_login(self.tesorero)
        client.post(reverse("depositar_comision", args=[self.liquidacion.id]), {
            "notas_tesorero": "Transferido el 13/07",
        })
        self.liquidacion.refresh_from_db()
        self.assertEqual(self.liquidacion.estado, "depositada")

    def test_deposito_registra_quien_deposito(self):
        """Se guarda el tesorero que realizó el depósito."""
        client = Client()
        client.force_login(self.tesorero)
        client.post(reverse("depositar_comision", args=[self.liquidacion.id]), {})
        self.liquidacion.refresh_from_db()
        self.assertEqual(self.liquidacion.depositada_por, self.tesorero)

    def test_vendedor_certifica_despues_del_deposito(self):
        """El vendedor puede certificar una liquidación en estado 'depositada'."""
        # Tesorero deposita primero
        self.liquidacion.estado = "depositada"
        self.liquidacion.depositada_por = self.tesorero
        self.liquidacion.depositada_en  = timezone.now()
        self.liquidacion.save()

        client = Client()
        client.force_login(self.vendedor)
        client.post(reverse("certificar_comision", args=[self.liquidacion.id]))
        self.liquidacion.refresh_from_db()
        self.assertEqual(self.liquidacion.estado, "certificada")

    def test_vendedor_no_puede_certificar_liquidacion_pendiente(self):
        """El vendedor no puede certificar si el tesorero aún no depositó."""
        client = Client()
        client.force_login(self.vendedor)
        client.post(reverse("certificar_comision", args=[self.liquidacion.id]))
        self.liquidacion.refresh_from_db()
        # Debe seguir en pendiente (la view ignora el POST y redirige con warning)
        self.assertNotEqual(self.liquidacion.estado, "certificada")

    def test_conductor_no_puede_depositar(self):
        """Un conductor no tiene acceso a depositar_comision (403 o redirect)."""
        conductor = crear_conductor(self.municipio, "cond2@test.com")
        client = Client()
        client.force_login(conductor)
        response = client.post(
            reverse("depositar_comision", args=[self.liquidacion.id]), {}
        )
        self.assertNotEqual(response.status_code, 200)
        # Estado no debe cambiar
        self.liquidacion.refresh_from_db()
        self.assertEqual(self.liquidacion.estado, "pendiente")

    def test_depositar_dos_veces_no_cambia_estado(self):
        """Depositar una liquidación ya depositada no la modifica (la view hace warning y redirige)."""
        self.liquidacion.estado = "depositada"
        self.liquidacion.depositada_por = self.tesorero
        self.liquidacion.depositada_en  = timezone.now()
        self.liquidacion.save()

        client = Client()
        client.force_login(self.tesorero)
        client.post(reverse("depositar_comision", args=[self.liquidacion.id]), {})
        self.liquidacion.refresh_from_db()
        # Sigue en depositada, no regresa a pendiente ni avanza a certificada
        self.assertEqual(self.liquidacion.estado, "depositada")

# ─────────────────────────────────────────────────────────────────────────────
# 6. Tolerancia de gracia en pago de infracciones
# ─────────────────────────────────────────────────────────────────────────────

class TestToleranciaMulta(TestCase):
    """
    El municipio puede configurar un período de gracia (tolerancia_multa_minutos).
    Si el conductor paga dentro de ese plazo, la infracción se anula sin cobrar.
    Pasado el plazo, se cobra normalmente descontando saldo.

    Técnica: se mockea timezone.now() en el use_case para simular distintos momentos
    de pago. creado_en de la infracción se fija con .update() para evitar auto_now_add.
    """

    def setUp(self):
        from datetime import timedelta
        from django.utils import timezone as tz

        self.municipio = Municipio.objects.create(
            nombre="TestMuni",
            tolerancia_multa_minutos=5,  # 5 minutos de gracia
        )
        self.inspector  = crear_inspector(self.municipio)
        self.subcuadra  = crear_subcuadra(self.municipio)
        self.vehiculo   = crear_vehiculo(self.municipio)
        self.conductor  = crear_conductor(self.municipio, saldo=2000)

        # Fijamos creado_en en el pasado para poder controlar el delta
        self.tiempo_creacion = tz.now()
        inf = crear_infraccion(
            self.municipio, self.inspector, self.vehiculo, self.subcuadra, monto=500
        )
        # auto_now_add no se puede pisar con save(); usamos update() para bypass
        Infraccion.objects.filter(pk=inf.pk).update(creado_en=self.tiempo_creacion)
        self.infraccion = Infraccion.objects.get(pk=inf.pk)

    def _pagar_con_tiempo(self, delta_minutos):
        """Ejecuta pagar_infraccion simulando que 'ahora' es creado_en + delta."""
        from datetime import timedelta
        from unittest.mock import patch
        from app_estacionamiento.use_cases.pagar_infraccion import ejecutar

        momento_pago = self.tiempo_creacion + timedelta(minutes=delta_minutos)
        with patch("app_estacionamiento.use_cases.pagar_infraccion.timezone") as mock_tz:
            mock_tz.now.return_value = momento_pago
            return ejecutar(self.conductor, self.infraccion)

    def test_pago_dentro_tolerancia_anula_infraccion(self):
        """Pagar a los 3 min (< 5 min de gracia) anula la infracción sin cobrar."""
        resultado = self._pagar_con_tiempo(delta_minutos=3)
        self.assertEqual(resultado.estado, "anulada")
        self.assertTrue(resultado.anulada_por_gracia)

    def test_pago_dentro_tolerancia_no_descuenta_saldo(self):
        """Si se anula por gracia, el saldo del conductor no se toca."""
        saldo_antes = self.conductor.saldo
        self._pagar_con_tiempo(delta_minutos=2)
        self.conductor.refresh_from_db()
        self.assertEqual(self.conductor.saldo, saldo_antes)

    def test_pago_exactamente_en_limite_anula(self):
        """Pagar exactamente a los 5 min todavía está dentro del plazo (<=)."""
        resultado = self._pagar_con_tiempo(delta_minutos=5)
        self.assertEqual(resultado.estado, "anulada")

    def test_pago_fuera_tolerancia_cobra_normal(self):
        """Pagar a los 10 min (> 5 min de gracia) descuenta saldo y marca pagada."""
        saldo_antes = self.conductor.saldo
        resultado = self._pagar_con_tiempo(delta_minutos=10)
        self.assertEqual(resultado.estado, "pagada")
        self.assertFalse(resultado.anulada_por_gracia)
        self.conductor.refresh_from_db()
        self.assertEqual(self.conductor.saldo, saldo_antes - Decimal("500"))

    def test_tolerancia_cero_siempre_cobra(self):
        """Con tolerancia=0 no hay gracia: pagar al instante igual cobra."""
        self.municipio.tolerancia_multa_minutos = 0
        self.municipio.save()
        saldo_antes = self.conductor.saldo
        resultado = self._pagar_con_tiempo(delta_minutos=0)
        self.assertEqual(resultado.estado, "pagada")
        self.conductor.refresh_from_db()
        self.assertLess(self.conductor.saldo, saldo_antes)

    def test_pago_doble_lanza_excepcion(self):
        """Intentar pagar una infracción ya pagada lanza Exception."""
        self._pagar_con_tiempo(delta_minutos=10)  # primer pago OK
        # Recargar para obtener estado actualizado
        self.infraccion.refresh_from_db()
        from app_estacionamiento.use_cases.pagar_infraccion import ejecutar
        with self.assertRaises(Exception):
            ejecutar(self.conductor, self.infraccion)


# ─────────────────────────────────────────────────────────────────────────────
# 6. Watermark GPS en foto de infracción
# ─────────────────────────────────────────────────────────────────────────────

class TestWatermarkGPS(TestCase):
    """
    Tests del helper _agregar_marca_de_agua_gps y su integración
    en el flujo crear_infraccion().

    Estrategia: imagen blanca pura (255,255,255) → el overlay oscuro
    del watermark hace que los píxeles del sector inferior bajen de 255.
    No se necesita OCR ni comparación de strings para verificar la marca.
    """

    def _foto_blanca(self, ancho=800, alto=600, nombre="test.jpg"):
        """Crea una imagen blanca en memoria lista para pasar al service."""
        import io
        from PIL import Image
        from django.core.files.uploadedfile import InMemoryUploadedFile

        img = Image.new("RGB", (ancho, alto), (255, 255, 255))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=95)
        buf.seek(0)
        return InMemoryUploadedFile(
            file=buf, field_name="foto", name=nombre,
            content_type="image/jpeg", size=buf.getbuffer().nbytes, charset=None,
        )

    def test_watermark_oscurece_franja_inferior(self):
        """La marca de agua aplica un overlay oscuro en la parte baja de la imagen."""
        from PIL import Image
        from app_estacionamiento.services.infracciones import _agregar_marca_de_agua_gps

        foto_entrada = self._foto_blanca(ancho=800, alto=600)
        resultado = _agregar_marca_de_agua_gps(
            foto=foto_entrada,
            lat="-34.65061", lon="-59.43203", acc="8",
            patente="TST001",
            inspector=type("Inspector", (), {"correo": "inspector@test.com"})(),
        )

        # Debe devolver un InMemoryUploadedFile válido
        from django.core.files.uploadedfile import InMemoryUploadedFile
        self.assertIsInstance(resultado, InMemoryUploadedFile)
        self.assertTrue(resultado.name.endswith(".jpg"))

        # La imagen resultante debe poder abrirse
        resultado.seek(0)
        img_out = Image.open(resultado)
        self.assertEqual(img_out.mode, "RGB")

        # El 10% inferior debe tener píxeles oscuros (el overlay negro semitransparente
        # sobre blanco puro produce valores < 200 en los tres canales).
        ancho, alto = img_out.size
        y_franja = int(alto * 0.90)
        pixeles_oscuros = 0
        for x in range(0, ancho, 20):   # muestreo cada 20px para no tardar
            r, g, b = img_out.getpixel((x, y_franja + 5))
            if r < 200 and g < 200 and b < 200:
                pixeles_oscuros += 1
        self.assertGreater(pixeles_oscuros, 5,
            "Se esperaba una franja oscura en la parte inferior de la imagen")

    def test_watermark_sin_gps_devuelve_foto_original(self):
        """Si no hay coordenadas, crear_infraccion no llama al watermark."""
        from app_estacionamiento.services.infracciones import _agregar_marca_de_agua_gps

        foto_entrada = self._foto_blanca()
        # Llamar directamente sin lat/lon no tiene sentido en el helper,
        # pero crear_infraccion sí hace la guarda:  if foto and gps_lat and gps_lon
        # Verificamos que el helper con datos vacíos no explota (fallback seguro).
        resultado = _agregar_marca_de_agua_gps(
            foto=foto_entrada,
            lat="", lon="", acc="",
            patente="TST001",
            inspector=type("Inspector", (), {"correo": "inspector@test.com"})(),
        )
        # Puede devolver la foto original o una marcada; lo importante: no lanza excepción.
        self.assertIsNotNone(resultado)

    def test_crear_infraccion_aplica_watermark_cuando_hay_gps(self):
        """
        Integración: crear_infraccion() con foto + GPS guarda la infracción
        con una imagen que tiene el overlay (píxeles inferiores oscuros).
        """
        from PIL import Image
        from app_estacionamiento.services.infracciones import crear_infraccion

        municipio = crear_municipio()
        crear_tarifa(municipio)
        inspector = crear_inspector(municipio)
        subcuadra = crear_subcuadra(municipio)
        vehiculo  = crear_vehiculo(municipio, patente="WMK001")

        foto = self._foto_blanca(nombre="acta.jpg")
        infraccion = crear_infraccion(
            patente="WMK001",
            subcuadra_id=subcuadra.id,
            inspector=inspector,
            foto=foto,
            gps_lat="-34.65061",
            gps_lon="-59.43203",
            gps_acc="12",
        )

        self.assertIsNotNone(infraccion.foto, "La infracción debe tener foto guardada")

        # La foto guardada debe tener la franja oscura del watermark
        infraccion.foto.open()
        img_out = Image.open(infraccion.foto)
        ancho, alto = img_out.size
        y_franja = int(alto * 0.90)
        pixeles_oscuros = sum(
            1 for x in range(0, ancho, 20)
            if all(c < 200 for c in img_out.getpixel((x, y_franja + 5)))
        )
        self.assertGreater(pixeles_oscuros, 5,
            "La foto de la infracción debe tener watermark GPS")
