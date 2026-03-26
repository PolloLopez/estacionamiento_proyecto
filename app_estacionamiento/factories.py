#app_estacionamiento/factories.py
# acá se implementa Factory

from django.utils import timezone
from datetime import timedelta
from .models import Estacionamiento

class EstacionamientoFactory:
    @staticmethod
    def crear(vehiculo, subcuadra, duracion, registrado_por=None):
        inicio = timezone.now()
        fin = inicio + timedelta(hours=float(duracion))

        estacionamiento = Estacionamiento.objects.create(
            vehiculo=vehiculo,
            subcuadra=subcuadra,
            hora_inicio=inicio,
            hora_fin=fin,
            registrado_por=registrado_por,
            activo=True
        )

        return estacionamiento