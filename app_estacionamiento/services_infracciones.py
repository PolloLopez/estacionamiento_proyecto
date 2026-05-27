# app_estacionamiento/services_infracciones.py

from django.utils import timezone
from datetime import timedelta
from app_estacionamiento.models import Infraccion
from app_estacionamiento.models import Estacionamiento, Vehiculo, Subcuadra


class ErrorInfraccion(Exception):
    pass


def crear_infraccion(*, patente, subcuadra_id, inspector, foto=None):

    # ==============================
    # VEHICULO
    # ==============================
    vehiculo = Vehiculo.objects.filter(patente=patente).first()
    if not vehiculo:
        raise ErrorInfraccion("Vehículo inexistente")

    # ==============================
    # SUBCUADRA
    # ==============================
    subcuadra = Subcuadra.objects.filter(
        id=subcuadra_id,
        municipio=inspector.municipio
    ).first()

    if not subcuadra:
        raise ErrorInfraccion("Subcuadra inválida")

    # ==============================
    # EXENCIONES
    # ==============================
    if vehiculo.exento_global:
        raise ErrorInfraccion("Exento TOTAL")

    if vehiculo.esta_exento_en(subcuadra):
        raise ErrorInfraccion("Exento en esta subcuadra")

    # ==============================
    # ESTACIONAMIENTO
    # ==============================
    estacionamiento = Estacionamiento.objects.filter(
        vehiculo=vehiculo,
        activo=True,
        municipio=inspector.municipio
    ).order_by("-hora_inicio").first()

    if estacionamiento:
        raise ErrorInfraccion("Tiene estacionamiento activo")

    # ==============================
    # REGLA 15 MIN
    # ==============================
    hace_15_min = timezone.now() - timedelta(minutes=15)

    ultima = Infraccion.objects.filter(
        vehiculo=vehiculo,
        municipio=inspector.municipio
    ).order_by("-id").first()

    if ultima and ultima.fecha_creacion >= hace_15_min:
        raise ErrorInfraccion("Ya existe una infracción reciente")

    # ==============================
    # CREACIÓN
    # ==============================
    infraccion = Infraccion.objects.create(
        vehiculo=vehiculo,
        inspector=inspector,
        municipio=inspector.municipio,
        subcuadra=subcuadra,
        estacionamiento=estacionamiento,
        foto=foto
    )

    return infraccion