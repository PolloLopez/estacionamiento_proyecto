# app_estacionamiento/services_verificacion.py

from django.urls import reverse
from .models import Estacionamiento
from app_estacionamiento.models import Vehiculo


def verificar_estado_vehiculo(patente, usuario):

    vehiculo = Vehiculo.objects.filter(patente=patente).first()

    # 🚫 NO REGISTRADO
    if not vehiculo:
        return {
            "patente": patente,
            "estado": "No registrado (Impago)",
            "estacionamiento_activo": False,
            "registrar_infraccion_url": reverse("inspectores_registrar_infraccion") + f"?patente={patente}"
        }

    # 🚫 EXENTO TOTAL
    if vehiculo.exento_global:
        return {
            "patente": vehiculo.patente,
            "estado": "Exento TOTAL",
            "estacionamiento_activo": True
        }

    # ⚠️ EXENTO PARCIAL
    subcuadras = vehiculo.subcuadras_exentas.all()
    if subcuadras.exists():
        return {
            "patente": vehiculo.patente,
            "estado": "Exento parcial",
            "estacionamiento_activo": False,
            "subcuadras_exentas": subcuadras,
            "registrar_infraccion_url": reverse("inspectores_registrar_infraccion") + f"?patente={vehiculo.patente}"
        }

    # 🚗 ESTACIONAMIENTO
    estacionamiento = Estacionamiento.objects.filter(
        vehiculo=vehiculo,
        activo=True,
        municipio=usuario.municipio
    ).first()

    if estacionamiento:
        return {
            "patente": vehiculo.patente,
            "estado": "Pagado",
            "estacionamiento_activo": True
        }

    return {
        "patente": vehiculo.patente,
        "estado": "Impago",
        "estacionamiento_activo": False,
        "registrar_infraccion_url": reverse("inspectores_registrar_infraccion") + f"?patente={vehiculo.patente}"
    }