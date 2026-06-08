# app_estacionamiento/services_infracciones.py

from django.utils import timezone
from datetime import timedelta
from app_estacionamiento.models import Infraccion, Estacionamiento, Vehiculo, Subcuadra, VerificacionInspector

class ErrorInfraccion(Exception):
    pass


def crear_infraccion(*, patente, subcuadra_id, inspector, foto=None):

    municipio = getattr(inspector, "municipio", None)
    if not municipio:
        raise ErrorInfraccion("Inspector sin municipio")

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
        municipio=municipio
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
        estado="ACTIVO",
        subcuadra__municipio=municipio
    ).order_by("-hora_inicio").first()

    if estacionamiento:
        raise ErrorInfraccion("Tiene estacionamiento activo")

    # ==============================
    # REGLA 15 MIN
    # ==============================
    hace_15_min = timezone.now() - timedelta(minutes=15)

    ultima = Infraccion.objects.filter(
        vehiculo=vehiculo,
        municipio=municipio
    ).order_by("-creado_en").first()

    if ultima and ultima.creado_en >= hace_15_min:
        raise ErrorInfraccion("Ya existe una infracción reciente")

    # ==============================
    # CREACIÓN
    # ==============================
    infraccion = Infraccion.objects.create(
        vehiculo=vehiculo,
        inspector=inspector,
        municipio=municipio,
        subcuadra=subcuadra,
        estacionamiento=estacionamiento,
        foto=foto
    )

    # Trazabilidad: marcar la última verificación como origen de esta infracción
    ultima_verificacion = VerificacionInspector.objects.filter(
        vehiculo=vehiculo,
        inspector=inspector
    ).order_by("-fecha").first()

    if ultima_verificacion:
        ultima_verificacion.infraccion_generada = True
        ultima_verificacion.save()

    return infraccion