# app_estacionamiento/services_infracciones.py

import io
import logging
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from django.core.files.uploadedfile import InMemoryUploadedFile
from app_estacionamiento.models import (
    Infraccion, Estacionamiento, Vehiculo, Subcuadra,
    VerificacionInspector, Tarifa
)

logger = logging.getLogger(__name__)


class ErrorInfraccion(Exception):
    pass


def _agregar_marca_de_agua_gps(foto, lat, lon, acc, patente, inspector):
    """
    Superpone coordenadas GPS, patente y fecha/hora sobre la foto.
    Retorna un InMemoryUploadedFile listo para el modelo,
    o la foto original si Pillow falla (para no bloquear el acta).
    """
    try:
        from PIL import Image, ImageDraw, ImageFont

        imagen = Image.open(foto)
        if imagen.mode not in ("RGB", "L"):
            imagen = imagen.convert("RGB")

        fecha_str = timezone.localtime().strftime("%d/%m/%Y %H:%M:%S")
        acc_str = f" (+-{acc}m)" if acc else ""
        texto_lineas = [
            f"Patente: {patente}",
            f"Inspector: {inspector.correo}",
            f"GPS: {lat}, {lon}{acc_str}",
            f"Fecha: {fecha_str}",
        ]

        ancho = imagen.width
        font_size = max(16, ancho // 40)

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
                font = ImageFont.load_default()

        linea_alto = font_size + 4
        bloque_alto = linea_alto * len(texto_lineas) + 10

        overlay = Image.new("RGBA", imagen.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        y_inicio = imagen.height - bloque_alto - 10
        overlay_draw.rectangle(
            [(0, y_inicio - 5), (ancho, imagen.height)],
            fill=(0, 0, 0, 160)
        )

        imagen_rgba = imagen.convert("RGBA")
        imagen_final = Image.alpha_composite(imagen_rgba, overlay).convert("RGB")
        draw_final = ImageDraw.Draw(imagen_final)

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


def crear_infraccion(
    *, patente, subcuadra_id, inspector,
    foto=None, gps_lat=None, gps_lon=None, gps_acc=None
):

    municipio = getattr(inspector, "municipio", None)
    if not municipio:
        raise ErrorInfraccion("Inspector sin municipio")

    # VEHICULO
    vehiculo = Vehiculo.objects.filter(patente=patente).first()
    if not vehiculo:
        raise ErrorInfraccion("Vehiculo inexistente")

    # SUBCUADRA
    subcuadra = Subcuadra.objects.filter(
        id=subcuadra_id,
        municipio=municipio
    ).first()
    if not subcuadra:
        raise ErrorInfraccion("Subcuadra invalida")

    # EXENCIONES
    if vehiculo.exento_global:
        raise ErrorInfraccion("Exento TOTAL")
    if vehiculo.esta_exento_en(subcuadra):
        raise ErrorInfraccion("Exento en esta subcuadra")

    # ESTACIONAMIENTO ACTIVO
    estacionamiento = Estacionamiento.objects.filter(
        vehiculo=vehiculo,
        estado="ACTIVO",
        subcuadra__municipio=municipio
    ).order_by("-hora_inicio").first()
    if estacionamiento:
        raise ErrorInfraccion("Tiene estacionamiento activo")

    # REGLA 15 MIN
    hace_15_min = timezone.now() - timedelta(minutes=15)
    ultima = Infraccion.objects.filter(
        vehiculo=vehiculo,
        municipio=municipio
    ).order_by("-creado_en").first()
    if ultima and ultima.creado_en >= hace_15_min:
        raise ErrorInfraccion("Ya existe una infraccion reciente")

    # MONTO desde tarifa del admin
    tarifa = Tarifa.objects.filter(municipio=municipio).first()
    monto = tarifa.monto_infraccion if tarifa else Decimal("0")

    # MARCA DE AGUA GPS en la foto
    foto_final = foto
    if foto and gps_lat and gps_lon:
        foto_final = _agregar_marca_de_agua_gps(
            foto=foto,
            lat=gps_lat,
            lon=gps_lon,
            acc=gps_acc,
            patente=patente,
            inspector=inspector,
        )

    # CREACION
    infraccion = Infraccion.objects.create(
        vehiculo=vehiculo,
        inspector=inspector,
        municipio=municipio,
        subcuadra=subcuadra,
        estacionamiento=estacionamiento,
        foto=foto_final,
        monto=monto,
    )

    # Trazabilidad
    ultima_verificacion = VerificacionInspector.objects.filter(
        vehiculo=vehiculo,
        inspector=inspector
    ).order_by("-fecha").first()
    if ultima_verificacion:
        ultima_verificacion.infraccion_generada = True
        ultima_verificacion.save()

    return infraccion
