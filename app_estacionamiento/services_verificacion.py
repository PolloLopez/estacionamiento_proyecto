# app_estacionamiento/services_verificacion.py

from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from app_estacionamiento.models import (
    Vehiculo, Estacionamiento, Estado,
    VerificacionInspector
)
from app_estacionamiento.domain.verificacion import ResultadoVerificacion
from app_estacionamiento.domain.enums import EstadoVehiculo


def _url_infraccion(patente):
    return reverse("inspectores_registrar_infraccion") + f"?patente={patente}"


def obtener_tolerancia():
    # TODO: después lo leemos desde configuración del admin
    return 15


def verificar_estado_vehiculo(patente, usuario, subcuadra):

    vehiculo = Vehiculo.objects.filter(patente=patente).first()

    if not vehiculo:
        return ResultadoVerificacion(
            patente=patente,
            estado=EstadoVehiculo.NO_REGISTRADO,
            estacionamiento_activo=False,
            registrar_infraccion_url=_url_infraccion(patente)
        )

    # registrar verificación
    VerificacionInspector.objects.create(
        vehiculo=vehiculo,
        inspector=usuario,
        subcuadra=subcuadra,
        resultado="verificado"
    )

    # EXENTO TOTAL
    if getattr(vehiculo, "exento_global", False):
        return ResultadoVerificacion(
            patente=patente,
            estado=EstadoVehiculo.EXENTO_TOTAL,
            estacionamiento_activo=True
        )

    # ESTACIONAMIENTO ACTIVO
    estacionamiento = Estacionamiento.objects.filter(
        vehiculo=vehiculo,
        estado=Estado.ACTIVO
    ).order_by("-hora_inicio").first()

    if estacionamiento:
        return ResultadoVerificacion(
            patente=patente,
            estado=EstadoVehiculo.PAGADO,
            estacionamiento_activo=True
        )

    # EXENTO PARCIAL
    if hasattr(vehiculo, "subcuadras_exentas"):
        if vehiculo.subcuadras_exentas.filter(id=subcuadra.id).exists():
            return ResultadoVerificacion(
                patente=patente,
                estado=EstadoVehiculo.EXENTO_PARCIAL,
                estacionamiento_activo=False
            )

    # TOLERANCIA (usar verificación anterior)
    ultima_verificacion = VerificacionInspector.objects.filter(
        vehiculo=vehiculo
    ).order_by("-fecha")[1:2].first()

    if ultima_verificacion:
        if timezone.now() - ultima_verificacion.fecha <= timedelta(minutes=15):
            return ResultadoVerificacion(
                patente=patente,
                estado=EstadoVehiculo.PENDIENTE_PAGO,
                estacionamiento_activo=False
            )

    # IMPAGO
    return ResultadoVerificacion(
        patente=patente,
        estado=EstadoVehiculo.IMPAGO,
        estacionamiento_activo=False,
        registrar_infraccion_url=_url_infraccion(patente)
    )