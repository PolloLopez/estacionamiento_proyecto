# app_estacionamiento/services_verificacion.py

from django.urls import reverse
from .models import Estacionamiento
from app_estacionamiento.models import Vehiculo
from dataclasses import dataclass
from typing import Optional

@dataclass
class ResultadoVerificacion:
    patente: str
    estado: str
    estacionamiento_activo: bool = False
    registrar_infraccion_url: Optional[str] = None
    subcuadras_exentas: Optional[object] = None

    def to_dict(self):
        """
        🔁 Compatibilidad con templates actuales
        Permite seguir usando resultado["estado"]
        """
        data = {
            "patente": self.patente,
            "estado": self.estado,
            "estacionamiento_activo": self.estacionamiento_activo,
        }

        if self.registrar_infraccion_url:
            data["registrar_infraccion_url"] = self.registrar_infraccion_url

        if self.subcuadras_exentas:
            data["subcuadras_exentas"] = self.subcuadras_exentas

        return data
    
        # 🔥 ESTO ES LO QUE TE FALTA
    def necesita_infraccion(self) -> bool:
        return self.registrar_infraccion_url is not None
    
def _url_infraccion(patente):
    return reverse("inspectores_registrar_infraccion") + f"?patente={patente}"


def verificar_estado_vehiculo(patente, usuario):

    vehiculo = Vehiculo.objects.filter(patente=patente).first()

    # 🚫 NO REGISTRADO
    if not vehiculo:
        return ResultadoVerificacion(
            patente=patente,
            estado="No registrado (Impago)", 
            estacionamiento_activo=False,
            registrar_infraccion_url=_url_infraccion(patente),
        )

    # 🚫 EXENTO TOTAL
    if vehiculo.exento_global:
        return ResultadoVerificacion(
            patente=vehiculo.patente,
            estado="Exento TOTAL",
            estacionamiento_activo=True,
        )

    # ⚠️ EXENTO PARCIAL
    subcuadras = vehiculo.subcuadras_exentas.all()
    if subcuadras.exists():
        return ResultadoVerificacion(
            patente=vehiculo.patente,
            estado="Exento parcial",
            estacionamiento_activo=False,
            subcuadras_exentas=subcuadras,
            registrar_infraccion_url=_url_infraccion(vehiculo.patente),
        )

    # 🚗 ESTACIONAMIENTO
    tiene_estacionamiento = Estacionamiento.objects.filter(
        vehiculo=vehiculo,
        activo=True,
        municipio=usuario.municipio
    ).exists()

    if tiene_estacionamiento:
        return ResultadoVerificacion(
            patente=vehiculo.patente,
            estado="Pagado",
            estacionamiento_activo=True,
        )

    # ❌ IMPAGO
    return ResultadoVerificacion(
        patente=vehiculo.patente,
        estado="Impago",
        estacionamiento_activo=False,
        registrar_infraccion_url=_url_infraccion(vehiculo.patente),
    )