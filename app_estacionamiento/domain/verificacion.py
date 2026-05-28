# app_estacionamiento/domain/verificacion.py
from dataclasses import dataclass
from typing import Optional
from app_estacionamiento.domain.enums import EstadoVehiculo

@dataclass
class ResultadoVerificacion:
    patente: str
    estado: EstadoVehiculo
    estacionamiento_activo: bool
    registrar_infraccion_url: Optional[str] = None
    subcuadras_exentas: list | None = None

    def necesita_infraccion(self) -> bool:
        return not self.estacionamiento_activo
    
    def css_class(self) -> str:
        return {
            EstadoVehiculo.NO_REGISTRADO: "danger",
            EstadoVehiculo.IMPAGO: "danger",
            EstadoVehiculo.PAGADO: "success",
            EstadoVehiculo.EXENTO_TOTAL: "info",
            EstadoVehiculo.EXENTO_PARCIAL: "warning",
        }[self.estado]

    # 👇 clave para no romper templates
    def estado_label(self):
        return self.estado.label()

    def to_dict(self):
        return {
            "patente": self.patente,
            "estado": self.estado.label(),  # 👈 string visible
            "estacionamiento_activo": self.estacionamiento_activo,
            "registrar_infraccion_url": self.registrar_infraccion_url,
            "subcuadras_exentas": self.subcuadras_exentas,
        }