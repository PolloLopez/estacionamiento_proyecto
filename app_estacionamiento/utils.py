# app_estacionamiento/utils.py
"""
Helpers puros de base de datos compartidos entre módulos.

Solo viven aquí funciones sin reglas de negocio:
accesos simples a DB que no dependen de configuración del municipio.

La lógica de negocio de horarios vive en: services/horarios.py
"""

from app_estacionamiento.models import Subcuadra

# Re-exportaciones para compatibilidad con imports existentes.
# Las funciones reales ahora viven en services/horarios.py
from .services.horarios import (  # noqa: F401
    puede_estacionar_ahora,
    calcular_opciones_duracion,
    cerrar_estacionamientos_vencidos_por_horario,
)


def get_subcuadra_default(municipio):
    """
    Retorna la subcuadra "Zona Única" del municipio.
    La crea automáticamente si no existe (para conductores sin calle asignada).
    """
    subcuadra, _ = Subcuadra.objects.get_or_create(
        calle="Zona Única",
        altura=0,
        municipio=municipio,
    )
    return subcuadra
