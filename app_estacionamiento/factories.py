#app_estacionamiento/factories.py

from decimal import Decimal

from django.utils import timezone
from datetime import timedelta
from .models import Estacionamiento

class EstacionamientoFactory:

    @staticmethod
    def crear(vehiculo, subcuadra, duracion, registrado_por):

        # cerrar activos del usuario
        Estacionamiento.objects.filter(
            registrado_por=registrado_por,
            activo=True
        ).update(activo=False)

        # cerrar activos del vehículo
        Estacionamiento.objects.filter(
            vehiculo=vehiculo,
            activo=True
        ).update(activo=False)
        if isinstance(duracion, Decimal):
            duracion = float(duracion)

        ahora = timezone.now()
        fin = ahora + timedelta(minutes=duracion)

        estacionamiento = Estacionamiento.objects.create(
            vehiculo=vehiculo,
            subcuadra=subcuadra,
            hora_inicio=ahora,
            hora_fin=fin,  
            activo=True,
            registrado_por=registrado_por
        )

        return estacionamiento