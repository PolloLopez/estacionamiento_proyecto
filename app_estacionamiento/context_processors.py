# app_estacionamiento/context_processors.py

"""
Context processor de branding.

Inyecta `municipio_branding` (instancia de Municipio) en cada template.
Cada template puede usar:
  {{ municipio_branding.logo.url }}      → URL del logo
  {{ municipio_branding.color_primario }} → color hex (#1a7a3c)
  {{ municipio_branding.nombre_sistema }} → texto del navbar
"""


def municipio_branding(request):
    """Detecta el municipio del usuario logueado y lo pone en el contexto."""
    from app_estacionamiento.models import Municipio

    municipio = None

    # Si el usuario está logueado y tiene municipio asignado, usarlo
    if request.user.is_authenticated:
        municipio = getattr(request.user, "municipio", None)

    # Fallback: primer municipio activo (p.ej. en la página de login)
    if municipio is None:
        municipio = Municipio.objects.filter(activo=True).first()

    return {"municipio_branding": municipio}
