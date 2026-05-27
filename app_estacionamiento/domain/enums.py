# app_estacionamiento/domain/enums.py

from enum import Enum


class EstadoVehiculo(Enum):
    NO_REGISTRADO = "no_registrado"
    IMPAGO = "impago"
    PAGADO = "pagado"
    EXENTO_TOTAL = "exento_total"
    EXENTO_PARCIAL = "exento_parcial"

    def label(self):
        if self == EstadoVehiculo.NO_REGISTRADO:
            return "No registrado (Impago)"
        if self == EstadoVehiculo.IMPAGO:
            return "Impago"
        if self == EstadoVehiculo.PAGADO:
            return "Pagado"
        if self == EstadoVehiculo.EXENTO_TOTAL:
            return "Exento TOTAL"
        if self == EstadoVehiculo.EXENTO_PARCIAL:
            return "Exento parcial"
        