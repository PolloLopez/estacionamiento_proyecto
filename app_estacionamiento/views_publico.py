# app_estacionamiento/views_publico.py
"""
Vistas públicas — sin login requerido.

Actualmente:
- dashboard_tv: pantalla de municipio en tiempo real, autenticada por token de solo lectura.
"""

from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from .models import Estacionamiento, Infraccion, Municipio


def dashboard_tv(request, token):
    """
    Dashboard de tiempo real para pantalla/TV del municipio.
    No requiere login — se autentica por token de solo lectura configurado en el municipio.

    Muestra:
    - Estacionamientos activos en este momento
    - Últimas 10 infracciones del día
    - Contadores rápidos (activos hoy, infracciones hoy)

    La página se auto-recarga cada 60 segundos vía meta-refresh + JS.
    El token vacío o inválido devuelve 404.
    """
    # token vacío = dashboard desactivado
    municipio = get_object_or_404(Municipio, token_tv=token, activo=True)
    if not token:
        from django.http import Http404
        raise Http404

    ahora = timezone.localtime()
    hoy   = ahora.date()

    estacionamientos_activos = (
        Estacionamiento.objects.filter(municipio=municipio, activo=True)
        .select_related("usuario", "vehiculo")
        .order_by("-inicio")[:50]
    )

    infracciones_hoy = (
        Infraccion.objects.filter(municipio=municipio, creado_en__date=hoy)
        .select_related("vehiculo", "inspector")
        .order_by("-creado_en")[:10]
    )

    total_activos     = estacionamientos_activos.count()
    total_infracciones = Infraccion.objects.filter(
        municipio=municipio, creado_en__date=hoy
    ).count()

    return render(request, "publico/dashboard_tv.html", {
        "municipio":               municipio,
        "estacionamientos_activos": estacionamientos_activos,
        "infracciones_hoy":        infracciones_hoy,
        "total_activos":           total_activos,
        "total_infracciones":      total_infracciones,
        "ahora":                   ahora,
    })
