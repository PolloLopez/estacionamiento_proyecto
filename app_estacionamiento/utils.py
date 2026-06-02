# utils.py

from app_estacionamiento.models import Subcuadra

def get_subcuadra_default(municipio):
    subcuadra, _ = Subcuadra.objects.get_or_create(
        calle="SIN DEFINIR",
        altura=0,
        municipio=municipio
    )
    return subcuadra