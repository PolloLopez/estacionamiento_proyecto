# app_estacionamiento/services/infracciones.py
"""
Lógica de negocio relacionada con infracciones de tránsito.

Responsabilidades:
- Crear infracciones (con validaciones de exención, tolerancia, monto, foto GPS)
- Cobrar infracciones en efectivo (desde el panel admin)
"""

import io
import logging
from datetime import timedelta
from decimal import Decimal

from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db import transaction
from django.utils import timezone

from app_estacionamiento.models import (
    Estacionamiento,
    Infraccion,
    MovimientoCaja,
    Subcuadra,
    Tarifa,
    VerificacionInspector,
    Vehiculo,
)

logger = logging.getLogger(__name__)


class ErrorInfraccion(Exception):
    """Error controlado durante la creación de una infracción."""
    pass


# ─────────────────────────────────────────────────────────────────────────────
# Helper privado
# ─────────────────────────────────────────────────────────────────────────────

def _agregar_marca_de_agua_gps(foto, lat, lon, acc, patente, inspector, subcuadra=None):
    """
    Superpone coordenadas GPS, patente y fecha/hora sobre la foto del acta.
    Retorna un InMemoryUploadedFile listo para el modelo,
    o la foto original si Pillow falla (para no bloquear el acta).
    """
    try:
        from PIL import Image, ImageDraw, ImageFont

        imagen = Image.open(foto)
        if imagen.mode not in ("RGB", "L"):
            imagen = imagen.convert("RGB")

        fecha_str = timezone.localtime().strftime("%d/%m/%Y %H:%M:%S")
        acc_str   = f" (+-{acc}m)" if acc else ""
        subcuadra_str = str(subcuadra) if subcuadra else ""
        nombre_inspector = f"{inspector.first_name} {inspector.last_name}".strip() or inspector.correo
        texto_lineas = [
            f"Patente: {patente}",
            f"Inspector: {nombre_inspector}",
            *([ subcuadra_str ] if subcuadra_str else []),
            f"GPS: {lat}, {lon}{acc_str}",
            fecha_str,
        ]

        ancho     = imagen.width
        font_size = max(32, ancho // 28)  # 2600px → ~93px, bien visible

        try:
            font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size
            )
        except Exception:
            try:
                font = ImageFont.truetype(
                    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", font_size
                )
            except Exception:
                # Pillow 10+ soporta size en load_default; si falla usamos el fijo
                try:
                    font = ImageFont.load_default(size=font_size)
                except TypeError:
                    font = ImageFont.load_default()

        linea_alto = font_size + 4
        bloque_alto = linea_alto * len(texto_lineas) + 10

        overlay      = Image.new("RGBA", imagen.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        y_inicio     = imagen.height - bloque_alto - 10
        overlay_draw.rectangle(
            [(0, y_inicio - 5), (ancho, imagen.height)],
            fill=(0, 0, 0, 160),
        )

        imagen_rgba  = imagen.convert("RGBA")
        imagen_final = Image.alpha_composite(imagen_rgba, overlay).convert("RGB")
        draw_final   = ImageDraw.Draw(imagen_final)

        y = y_inicio
        for linea in texto_lineas:
            draw_final.text((10, y), linea, font=font, fill=(255, 255, 255))
            y += linea_alto

        buffer = io.BytesIO()
        imagen_final.save(buffer, format="JPEG", quality=88)
        buffer.seek(0)

        nombre = f"infraccion_{patente}_{timezone.now().strftime('%Y%m%d%H%M%S')}.jpg"
        return InMemoryUploadedFile(
            file=buffer,
            field_name="foto",
            name=nombre,
            content_type="image/jpeg",
            size=buffer.getbuffer().nbytes,
            charset=None,
        )

    except Exception as e:
        logger.warning("No se pudo agregar marca de agua GPS: %s", e)
        return foto


# ─────────────────────────────────────────────────────────────────────────────
# Servicios públicos
# ─────────────────────────────────────────────────────────────────────────────

def crear_infraccion(
    *, patente, subcuadra_id, inspector,
    foto=None, gps_lat=None, gps_lon=None, gps_acc=None
):
    """
    Crea una infracción para el vehículo indicado.

    Validaciones en orden:
    1. Vehículo existente
    2. Subcuadra válida del municipio
    3. Exención global
    4. Exención parcial en subcuadra
    5. Estacionamiento activo (no se puede infraccionar)
    6. Regla de 15 minutos entre infracciones

    Si todo es válido, crea la Infraccion y registra la trazabilidad.
    Lanza ErrorInfraccion con mensaje descriptivo ante cualquier bloqueo.
    """
    municipio = getattr(inspector, "municipio", None)
    if not municipio:
        raise ErrorInfraccion("Inspector sin municipio")

    vehiculo = Vehiculo.objects.filter(patente=patente).first()
    if not vehiculo:
        raise ErrorInfraccion("Vehiculo inexistente")

    subcuadra = Subcuadra.objects.filter(
        id=subcuadra_id, municipio=municipio
    ).first()
    if not subcuadra:
        raise ErrorInfraccion("Subcuadra invalida")

    if vehiculo.exento_global:
        raise ErrorInfraccion("Exento TOTAL")
    if vehiculo.esta_exento_en(subcuadra):
        raise ErrorInfraccion("Exento en esta subcuadra")

    estacionamiento = Estacionamiento.objects.filter(
        vehiculo=vehiculo,
        estado="ACTIVO",
        subcuadra__municipio=municipio,
    ).order_by("-hora_inicio").first()
    if estacionamiento:
        raise ErrorInfraccion("Tiene estacionamiento activo")

    hace_15_min = timezone.now() - timedelta(minutes=15)
    ultima = Infraccion.objects.filter(
        vehiculo=vehiculo, municipio=municipio
    ).order_by("-creado_en").first()
    if ultima and ultima.creado_en >= hace_15_min:
        raise ErrorInfraccion("Ya existe una infraccion reciente")

    tarifa = Tarifa.objects.filter(municipio=municipio).first()
    monto  = tarifa.monto_infraccion if tarifa else Decimal("0")

    foto_final = foto
    if foto and gps_lat and gps_lon:
        foto_final = _agregar_marca_de_agua_gps(
            foto=foto, lat=gps_lat, lon=gps_lon, acc=gps_acc,
            patente=patente, inspector=inspector, subcuadra=subcuadra,
        )

    # Intentar crear con foto. Si el storage (Cloudinary) falla, guardar sin foto
    # para no perder el acta. El inspector puede agregar la foto manualmente si hace falta.
    try:
        infraccion = Infraccion.objects.create(
            vehiculo=vehiculo,
            inspector=inspector,
            municipio=municipio,
            subcuadra=subcuadra,
            estacionamiento=estacionamiento,
            foto=foto_final,
            monto=monto,
        )
    except Exception as e:
        logger.error("Error al guardar foto de infraccion (¿Cloudinary?): %s", e)
        infraccion = Infraccion.objects.create(
            vehiculo=vehiculo,
            inspector=inspector,
            municipio=municipio,
            subcuadra=subcuadra,
            estacionamiento=estacionamiento,
            foto=None,
            monto=monto,
        )

    # Trazabilidad: marcar que la última verificación generó infracción
    ultima_verificacion = VerificacionInspector.objects.filter(
        vehiculo=vehiculo, inspector=inspector
    ).order_by("-fecha").first()
    if ultima_verificacion:
        ultima_verificacion.infraccion_generada = True
        ultima_verificacion.save()

    return infraccion


def cobrar_infraccion_efectivo(infraccion, cobrador):
    """
    Cobra una infracción en efectivo desde el panel admin.

    - Marca la infracción como pagada (con fecha_pago).
    - Registra el ingreso en la caja del cobrador (con su comisión).
    - Usa select_for_update para evitar doble cobro concurrente.

    Parámetros:
        infraccion: instancia de Infraccion (debe estar en estado 'pendiente')
        cobrador: instancia de Usuario admin que cobra

    Retorna:
        La infraccion actualizada.

    Lanza:
        ValueError si la infracción ya fue procesada.
    """
    municipio = getattr(cobrador, "municipio", None)

    with transaction.atomic():
        inf = Infraccion.objects.select_for_update().get(pk=infraccion.pk)

        if inf.estado != "pendiente":
            raise ValueError(f"La infracción #{inf.id} ya fue procesada (estado: {inf.estado}).")

        inf.estado     = "pagada"
        inf.fecha_pago = timezone.now()
        inf.save(update_fields=["estado", "fecha_pago"])

        comision_pct = (getattr(municipio, "comision_vendedor", None) or 0)
        comision     = round(inf.monto * comision_pct / 100, 2)

        MovimientoCaja.objects.create(
            usuario=cobrador,
            monto=inf.monto,
            tipo="ingreso",
            medio_pago="efectivo",
            comision_monto=comision,
            descripcion=(
                f"Cobro en efectivo infracción #{inf.id} — {inf.vehiculo.patente}"
            ),
        )

    return inf


# ─────────────────────────────────────────────────────────────────────────────
# Tolerancia de gracia — helper compartido
# ─────────────────────────────────────────────────────────────────────────────

# Margen para evitar cobrar infracciones por pocos segundos de diferencia
MARGEN_TOLERANCIA_SEGUNDOS = 60


def calcular_estado_tolerancia(infraccion, municipio, ahora=None):
    """
    Determina si una infracción está dentro del período de gracia.

    Incluye MARGEN_TOLERANCIA_SEGUNDOS para evitar cobrar por diferencias
    de pocos segundos (por ejemplo: el conductor llega 2 segundos tarde).

    Parámetros:
        infraccion: instancia de Infraccion (debe tener creado_en)
        municipio:  instancia de Municipio (debe tener tolerancia_multa_minutos)
        ahora:      datetime con timezone (default: timezone.now())

    Retorna dict con:
        dentro_tolerancia (bool)  — True si aún está dentro del período de gracia
        tolerancia_min    (int)   — minutos configurados en el municipio
        hora_verificacion (datetime) — cuándo se labró la infracción
        hora_fin_gracia   (datetime) — cuándo vence el período de gracia
    """
    if ahora is None:
        ahora = timezone.now()

    tolerancia_min  = getattr(municipio, "tolerancia_multa_minutos", 0) or 0
    hora_fin_gracia = infraccion.creado_en + timedelta(minutes=tolerancia_min)

    if tolerancia_min <= 0:
        dentro = False
    else:
        elapsed = ahora - infraccion.creado_en
        dentro  = elapsed <= timedelta(
            minutes=tolerancia_min,
            seconds=MARGEN_TOLERANCIA_SEGUNDOS,
        )

    return {
        "dentro_tolerancia": dentro,
        "tolerancia_min":    tolerancia_min,
        "hora_verificacion": infraccion.creado_en,
        "hora_fin_gracia":   hora_fin_gracia,
    }
