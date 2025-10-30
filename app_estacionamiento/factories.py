#app_estacionamiento/factories.py
# acá se implementa Factory
from .models import Estacionamiento

class EstacionamientoFactory:
    @staticmethod
    def crear(vehiculo, subcuadra):
        """
        Crea un nuevo objeto Estacionamiento con los datos dados.
        # acá se implementa Factory
        """
        return Estacionamiento.objects.create(vehiculo=vehiculo, subcuadra=subcuadra)
