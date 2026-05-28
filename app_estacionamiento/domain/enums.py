# app_estacionamiento/domain/enums.py

from enum import Enum


class EstadoVehiculo(Enum):
    NO_REGISTRADO = "no_registrado"
    IMPAGO = "impago"
    PAGADO = "pagado"
    EXENTO_TOTAL = "exento_total"
    EXENTO_PARCIAL = "exento_parcial"
    PENDIENTE_PAGO = "pendiente_pago"

    @property
    def label(self):
        mapping = {
            self.NO_REGISTRADO: "No registrado (Impago)",
            self.IMPAGO: "Impago",
            self.PAGADO: "Pagado",
            self.EXENTO_TOTAL: "Exento TOTAL",
            self.EXENTO_PARCIAL: "Exento parcial",
            self.PENDIENTE_PAGO: "Pendiente de pago",
        }
        return mapping[self]