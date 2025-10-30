#app_estacionamiento/estrategias.py
from .models import Tarifa

class EstrategiaExencion:
    def calcular(self, vehiculo, subcuadra, duracion_horas):
        # Exento en toda la zona
        if vehiculo.exento_en_zona:
            return 0
        # Exento en esta subcuadra
        if vehiculo.subcuadras_exentas.filter(id=subcuadra.id).exists():
            return 0
        # Tarifa normal
        tarifa = Tarifa.objects.last() or Tarifa(precio_por_hora=100)
        return duracion_horas * tarifa.precio_por_hora
