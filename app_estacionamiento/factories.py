#app_estacionamiento/factories.py

from django.utils import timezone
from datetime import timedelta
from .models import Estacionamiento

class EstacionamientoFactory:

    @staticmethod
    def crear(vehiculo, subcuadra, duracion, registrado_por):

        Estacionamiento.objects.filter(
            registrado_por=registrado_por,
            activo=True
        ).update(activo=False)

        # 🔥 Cerrar activos previos del mismo vehículo
        Estacionamiento.objects.filter(
            vehiculo=vehiculo,
            activo=True
        ).update(activo=False)

        estacionamiento = Estacionamiento.objects.create(
            vehiculo=vehiculo,
            subcuadra=subcuadra,
            hora_inicio=timezone.now(),
            activo=True,
            registrado_por=registrado_por
        )
        return estacionamiento