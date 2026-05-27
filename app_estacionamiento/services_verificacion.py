# app_estacionamiento/services_verificacion.py

from django.urls import reverse
from app_estacionamiento.models import Vehiculo, Estacionamiento
from dataclasses import dataclass

from app_estacionamiento.domain.verificacion import ResultadoVerificacion
from app_estacionamiento.domain.enums import EstadoVehiculo
from typing import Optional
   
def _url_infraccion(patente):
    return reverse("inspectores_registrar_infraccion") + f"?patente={patente}"

def verificar_estado_vehiculo(patente, usuario):

    vehiculo = Vehiculo.objects.filter(patente=patente).first()

    # 🚫 NO REGISTRADO
    if not vehiculo:
        return ResultadoVerificacion(
            patente=patente,
            estado=EstadoVehiculo.NO_REGISTRADO,
            estacionamiento_activo=False,
            registrar_infraccion_url=reverse("inspectores_registrar_infraccion") + f"?patente={patente}"
        )

    # 🚫 EXENTO TOTAL
    if vehiculo.exento_global:
        return ResultadoVerificacion(
            patente=vehiculo.patente,
            estado=EstadoVehiculo.EXENTO_TOTAL,
            estacionamiento_activo=True
        )

    # ⚠️ EXENTO PARCIAL
    subcuadras = vehiculo.subcuadras_exentas.all()
    if subcuadras.exists():
        return ResultadoVerificacion(
            patente=vehiculo.patente,
            estado=EstadoVehiculo.EXENTO_PARCIAL,
            estacionamiento_activo=False,
            subcuadras_exentas=subcuadras,
            registrar_infraccion_url=reverse("inspectores_registrar_infraccion") + f"?patente={vehiculo.patente}"
        )

    # 🚗 ESTACIONAMIENTO
    estacionamiento = Estacionamiento.objects.filter(
        vehiculo=vehiculo,
        activo=True,
        municipio=usuario.municipio
    ).first()

    if estacionamiento:
        return ResultadoVerificacion(
            patente=vehiculo.patente,
            estado=EstadoVehiculo.PAGADO,
            estacionamiento_activo=True
        )

    # ❌ IMPAGO
    return ResultadoVerificacion(
        patente=vehiculo.patente,
        estado=EstadoVehiculo.IMPAGO,
        estacionamiento_activo=False,
        registrar_infraccion_url=reverse("inspectores_registrar_infraccion") + f"?patente={vehiculo.patente}"
    )
