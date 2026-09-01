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
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .decorators import require_role
from .models import CierreCaja, LiquidacionComision, Rendicion


@require_role("tesorero")
def panel_tesorero(request):
    """
    Panel principal del tesorero.
    Muestra rendiciones de administradores y liquidaciones de comisiones de vendedores.
    Las rendiciones se separan en pendientes (acción requerida) e historial.
    """
    municipio = request.user.municipio

    qs_rendiciones   = Rendicion.objects.filter(municipio=municipio).select_related("admin")
    qs_liquidaciones = LiquidacionComision.objects.filter(municipio=municipio).select_related("vendedor")

    # Separar pendientes del historial para que el tesorero vea primero qué necesita acción
    rendiciones_pendientes = qs_rendiciones.filter(estado="pendiente").order_by("-creado_en")
    rendiciones_historial  = qs_rendiciones.exclude(estado="pendiente").order_by("-validado_en")[:30]

    # Total de neto pendiente de validar
    total_neto_pendiente = (
        rendiciones_pendientes.aggregate(total=Sum("total_neto"))["total"] or 0
    )

    pendientes_rendicion   = rendiciones_pendientes.count()
    pendientes_liquidacion = qs_liquidaciones.filter(estado="pendiente").count()

    liquidaciones = qs_liquidaciones.order_by("-creado_en")[:50]

    # Cierres de admin sin certificar — válvula de escape para el tesorero.
    # Solo cierres de admins (es_admin=True): inspectores y vendedores los certifica el admin.
    cierres_admin_sin_certificar = CierreCaja.objects.filter(
        usuario__municipio=municipio,
        usuario__es_admin=True,
        certificado=False,
    ).select_related("usuario").order_by("-fecha_cierre")

    return render(request, "tesorero/panel_tesorero.html", {
        "rendiciones_pendientes":        rendiciones_pendientes,
        "rendiciones_historial":         rendiciones_historial,
        "total_neto_pendiente":          total_neto_pendiente,
        "liquidaciones":                 liquidaciones,
        "pendientes_rendicion":          pendientes_rendicion,
        "pendientes_liquidacion":        pendientes_liquidacion,
        "cierres_admin_sin_certificar":  cierres_admin_sin_certificar,
    })


@require_role("tesorero")
def validar_rendicion(request, rendicion_id):
    """
    El tesorero marca una rendición como validada (recibida) u observada.
    Solo acepta POST. Actualiza estado, registra quién validó y cuándo.
    """
    municipio = request.user.municipio
    rendicion = get_object_or_404(Rendicion, id=rendicion_id, municipio=municipio)

    if rendicion.estado != "pendiente":
        messages.warning(request, "Esta rendición ya fue procesada.")
        return redirect("panel_tesorero")

    if request.method != "POST":
        return redirect("panel_tesorero")

    accion = request.POST.get("accion", "validar")
    notas  = request.POST.get("notas_tesorero", "").strip()

    estado_nuevo = "validada" if accion == "validar" else "observada"
    with transaction.atomic():
        rendicion.estado          = estado_nuevo
        rendicion.tesorero        = request.user
        rendicion.validado_en     = timezone.now()
        rendicion.notas_tesorero  = notas
        rendicion.save(update_fields=["estado", "tesorero", "validado_en", "notas_tesorero"])

    label = "validada ✅" if estado_nuevo == "validada" else "observada ⚠️"
    messages.success(request, f"Rendición #{rendicion.id} marcada como {label}.")
    return redirect("panel_tesorero")


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
