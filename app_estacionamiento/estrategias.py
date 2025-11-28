#app_estacionamiento/estrategias.py
from decimal import Decimal
from .models import Tarifa

class EstrategiaExencion:
    def calcular(self, vehiculo, subcuadra, duracion_horas):
        # Exento en toda la zona
        if vehiculo.exento_global:
            return Decimal("0.00")
        # Exento en esta subcuadra
        if vehiculo.subcuadras_exentas.filter(id=subcuadra.id).exists():
            return Decimal("0.00")
        # Tarifa normal
        tarifa = Tarifa.objects.last()
        if not tarifa:
            return Decimal(str(duracion_horas)) * Decimal("100.00")
        return Decimal(str(duracion_horas)) * tarifa.precio_por_hora
