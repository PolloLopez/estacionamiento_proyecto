# app_estacionamiento/estrategias.py

from decimal import Decimal
from .models import Tarifa

class EstrategiaExencion:
    """
    Estrategia de cálculo de costo.
    - Si el vehículo está exento globalmente → costo 0.
    - Si la subcuadra está exenta para ese vehículo → costo 0.
    - Si no hay tarifa definida en BD → usa un valor por defecto (ej. 100 por hora).
    - Si hay tarifa → multiplica duración por precio_por_hora.
    """

    def calcular(self, vehiculo, subcuadra, duracion_horas: float) -> Decimal:
        # Caso exento global
        if vehiculo.exento_global:
            return Decimal("0.00")

        # Caso exento parcial
        if subcuadra and vehiculo.subcuadras_exentas.filter(id=subcuadra.id).exists():
            return Decimal("0.00")

        # Buscar tarifa en BD
        tarifa = Tarifa.objects.first()
        if not tarifa:
            # Valor por defecto si no hay tarifa configurada
            return Decimal(str(duracion_horas)).quantize(Decimal("1")) * Decimal("100.00")

        # Calcular costo con tarifa
        costo = Decimal(str(duracion_horas)) * Decimal(str(tarifa.precio_por_hora))
        return costo.quantize(Decimal("0.01"))
