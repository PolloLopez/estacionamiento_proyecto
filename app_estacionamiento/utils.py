# utils.py

from app_estacionamiento.models import Subcuadra

def get_subcuadra_default(municipio):
    subcuadra = Subcuadra.objects.filter(
        calle="SIN DEFINIR",
        altura=0,
        municipio=municipio
    ).first()

    if subcuadra:
        return subcuadra

    return Subcuadra.objects.create(
        calle="SIN DEFINIR",
        altura=0,
        municipio=municipio
    )