#app_estacionamiento/factories.py
# acá se implementa Factory
from .models import Estacionamiento

class EstacionamientoFactory:
    @staticmethod
    def crear(vehiculo, subcuadra, duracion, registrado_por=None):
        estacionamiento = Estacionamiento.objects.create(
            vehiculo=vehiculo,
            subcuadra=subcuadra,
            registrado_por=registrado_por
        )
        # lógica de duración, costo, etc.
        return estacionamiento

