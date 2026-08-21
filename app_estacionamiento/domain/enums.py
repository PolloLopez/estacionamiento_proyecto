# app_estacionamiento/domain/enums.py

from enum import Enum

# Minutos mínimos entre dos infracciones al mismo vehículo en el mismo municipio.
# Usado en services/verificacion.py (para mostrar el estado al inspector)
# y en services/infracciones.py (como segunda barrera al crear el acta).
MINUTOS_ENTRE_INFRACCIONES = 15


class EstadoVehiculo(Enum):
    NO_REGISTRADO      = "no_registrado"       # nunca estacionó
    IMPAGO             = "impago"               # vencido o sin pago
    PAGADO             = "pagado"
    ABONO_ACTIVO       = "abono_activo"         # tiene abono mensual vigente
    EXENTO_TOTAL       = "exento_total"         # exento global
    EXENTO_PARCIAL     = "exento_parcial"       # exento en ciertas subcuadras
    PENDIENTE_PAGO     = "pendiente_pago"       # dentro de ventana de tolerancia del inspector
    INFRACCION_RECIENTE = "infraccion_reciente" # ya infraccionado en los últimos N minutos

    @property
    def label(self):
        mapping = {
            self.NO_REGISTRADO:       "No registrado (Impago)",
            self.IMPAGO:              "Impago",
            self.PAGADO:              "Pagado",
            self.ABONO_ACTIVO:        "Abono mensual activo",
            self.EXENTO_TOTAL:        "Exento TOTAL",
            self.EXENTO_PARCIAL:      "Exento parcial",
            self.PENDIENTE_PAGO:      "Pendiente de pago",
            self.INFRACCION_RECIENTE: "Infracción reciente",
        }
        return mapping[self]
