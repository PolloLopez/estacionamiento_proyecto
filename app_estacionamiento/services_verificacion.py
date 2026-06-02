# app_estacionamiento/services_verificacion.py

from django.urls import reverse
from app_estacionamiento.models import Vehiculo, Estacionamiento
from app_estacionamiento.domain.verificacion import ResultadoVerificacion
from app_estacionamiento.domain.enums import EstadoVehiculo


def _url_infraccion(patente):
    return reverse("inspectores_registrar_infraccion") + f"?patente={patente}"


def verificar_estado_vehiculo(patente, usuario):

    vehiculo = Vehiculo.objects.filter(patente=patente).first()

    if not vehiculo:
        return ResultadoVerificacion(
            patente=patente,
            estado=EstadoVehiculo.NO_REGISTRADO,
            estacionamiento_activo=False,
            registrar_infraccion_url=_url_infraccion(patente)
        )

    # ✅ EXENTO TOTAL
    if getattr(vehiculo, "exento_global", False):
        return ResultadoVerificacion(
            patente=patente,
            estado=EstadoVehiculo.EXENTO_TOTAL,
            estacionamiento_activo=True
        )

    # 🔥 EXENTO PARCIAL (clave real)
    subcuadras_exentas = []

    if hasattr(vehiculo, "subcuadras_exentas"):
        subcuadras_exentas = vehiculo.subcuadras_exentas.all()

    if subcuadras_exentas and subcuadras_exentas.exists():
        return ResultadoVerificacion(
            patente=patente,
            estado=EstadoVehiculo.EXENTO_PARCIAL,
            estacionamiento_activo=False,
            registrar_infraccion_url=_url_infraccion(patente),
            subcuadras_exentas=subcuadras_exentas
        )

    # ✅ ESTACIONAMIENTO ACTIVO
    est_activo = Estacionamiento.objects.filter(
        vehiculo=vehiculo,
        activo=True
    ).exists()

    if est_activo:
        return ResultadoVerificacion(
            patente=patente,
            estado=EstadoVehiculo.PAGADO,
            estacionamiento_activo=True
        )

    # ❌ IMPAGO
    return ResultadoVerificacion(
        patente=patente,
        estado=EstadoVehiculo.IMPAGO,
        estacionamiento_activo=False,
        registrar_infraccion_url=_url_infraccion(patente)
    )