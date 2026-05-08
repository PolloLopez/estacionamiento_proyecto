# utils.py

from app_estacionamiento.models import Subcuadra


def get_subcuadra_default(municipio):
    return Subcuadra.objects.get_or_create(
        calle="Zona Única",
        altura=0,
        municipio=municipio
    )[0]