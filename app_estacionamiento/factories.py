#app_estacionamiento/factories.py

from decimal import Decimal

from django.utils import timezone
from datetime import timedelta
from .models import Estacionamiento

class EstacionamientoFactory:

    @staticmethod
    def crear(*, usuario, vehiculo, subcuadra, duracion, costo_base):

        estacionamiento = Estacionamiento.objects.create(
            usuario=usuario,
            vehiculo=vehiculo,
            subcuadra=subcuadra,
            duracion_min=duracion,
            costo_base=costo_base,
            estado="ACTIVO"
        )

        # cerrar otros activos del mismo vehículo
        Estacionamiento.objects.filter(
            vehiculo=vehiculo,
            estado="ACTIVO"
        ).exclude(id=estacionamiento.id).update(estado="FINALIZADO")

        return estacionamiento