# utils.py

from app_estacionamiento.models import Subcuadra

def get_subcuadra_default(municipio):
    # "Zona Única" es la subcuadra para conductores que no tienen calle asignada.
    # Se crea automáticamente si no existe.
    subcuadra, _ = Subcuadra.objects.get_or_create(
        calle="Zona Única",
        altura=0,
        municipio=municipio
    )
    return subcuadra