# app_estacionamiento/views_tesorero.py
"""
Vistas del rol Tesorero.

Responsabilidades:
- Ver rendiciones pendientes de los administradores
- Ver liquidaciones de comisiones pendientes de los vendedores
- Registrar el depósito de una liquidación de comisión
"""

from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .decorators import require_role
from .models import LiquidacionComision, Rendicion


@require_role("tesorero")
def panel_tesorero(request):
    """
    Panel principal del tesorero.
    Muestra rendiciones de administradores y liquidaciones de comisiones de vendedores,
    con el conteo de pendientes de cada tipo.
    """
    municipio = request.user.municipio

    qs_rendiciones = Rendicion.objects.filter(municipio=municipio).select_related("admin")
    qs_liquidaciones = LiquidacionComision.objects.filter(municipio=municipio).select_related("vendedor")

    # Contar pendientes antes de aplicar el slice (no se puede filtrar sobre queryset sliceado)
    pendientes_rendicion   = qs_rendiciones.filter(estado="pendiente").count()
    pendientes_liquidacion = qs_liquidaciones.filter(estado="pendiente").count()

    rendiciones   = qs_rendiciones.order_by("-creado_en")[:50]
    liquidaciones = qs_liquidaciones.order_by("-creado_en")[:50]

    return render(request, "tesorero/panel_tesorero.html", {
        "rendiciones":            rendiciones,
        "liquidaciones":          liquidaciones,
        "pendientes_rendicion":   pendientes_rendicion,
        "pendientes_liquidacion": pendientes_liquidacion,
    })


@require_role("tesorero")
def depositar_comision(request, liquidacion_id):
    """
    Registra el depósito de una liquidación de comisión al vendedor.

    Parámetros:
        liquidacion_id: ID de la LiquidacionComision a depositar

    Solo procesa liquidaciones en estado 'pendiente'.
    Guarda quién depositó, cuándo y notas opcionales.
    """
    municipio   = request.user.municipio
    liquidacion = get_object_or_404(LiquidacionComision, id=liquidacion_id, municipio=municipio)

    if liquidacion.estado != "pendiente":
        messages.warning(request, "Esta liquidación ya fue procesada.")
        return redirect("panel_tesorero")

    if request.method == "POST":
        notas = request.POST.get("notas_tesorero", "").strip()
        with transaction.atomic():
            liquidacion.estado         = "depositada"
            liquidacion.depositada_en  = timezone.now()
            liquidacion.depositada_por = request.user
            liquidacion.notas_tesorero = notas
            liquidacion.save(update_fields=[
                "estado", "depositada_en", "depositada_por", "notas_tesorero"
            ])
        messages.success(request, f"Depósito registrado para {liquidacion.vendedor.nombre_completo()}.")
        return redirect("panel_tesorero")

    return render(request, "tesorero/depositar_comision.html", {
        "liquidacion": liquidacion,
    })
