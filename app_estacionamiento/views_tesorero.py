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
from .models import CierreCaja, LiquidacionComision, LiquidacionPlataforma, Rendicion


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

    # Liquidaciones de plataforma (lo que el municipio le debe/pagó a Leandro)
    liq_plataforma_pendientes = LiquidacionPlataforma.objects.filter(
        municipio=municipio,
        estado__in=("pendiente_pago", "observada"),
    ).order_by("-periodo_fin")

    liq_plataforma_recientes = LiquidacionPlataforma.objects.filter(
        municipio=municipio,
    ).order_by("-periodo_fin")[:10]

    return render(request, "tesorero/panel_tesorero.html", {
        "rendiciones_pendientes":        rendiciones_pendientes,
        "rendiciones_historial":         rendiciones_historial,
        "total_neto_pendiente":          total_neto_pendiente,
        "liquidaciones":                 liquidaciones,
        "pendientes_rendicion":          pendientes_rendicion,
        "pendientes_liquidacion":        pendientes_liquidacion,
        "cierres_admin_sin_certificar":  cierres_admin_sin_certificar,
        "liq_plataforma_pendientes":     liq_plataforma_pendientes,
        "liq_plataforma_recientes":      liq_plataforma_recientes,
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


# ─────────────────────────────────────────────────────────────────────────────
# Liquidaciones de plataforma (el municipio paga a Leandro por el sistema)
# ─────────────────────────────────────────────────────────────────────────────

@require_role("tesorero")
def mis_liquidaciones_plataforma(request):
    """Lista completa de liquidaciones de la plataforma para el municipio del tesorero."""
    municipio = request.user.municipio
    qs = LiquidacionPlataforma.objects.filter(municipio=municipio)

    estado_filtro = request.GET.get("estado", "").strip()
    if estado_filtro:
        qs = qs.filter(estado=estado_filtro)

    liquidaciones = qs.order_by("-periodo_fin", "-creado_en")
    pendientes_count = LiquidacionPlataforma.objects.filter(
        municipio=municipio, estado__in=("pendiente_pago", "observada")
    ).count()

    return render(request, "tesorero/liquidaciones_plataforma.html", {
        "liquidaciones":   liquidaciones,
        "municipio":       municipio,
        "estado_filtro":   estado_filtro,
        "pendientes_count": pendientes_count,
        "estados":         LiquidacionPlataforma.ESTADOS,
    })


@require_role("tesorero")
def crear_liquidacion_tesorero(request):
    """
    El tesorero inicia una liquidación espontánea: elige el período, calcula
    los montos según la config del municipio, sube el comprobante de pago y
    la envía al superadmin.
    """
    from datetime import date as _date
    from decimal import Decimal

    municipio = request.user.municipio

    if request.method == "POST":
        desde_str = request.POST.get("periodo_inicio", "")
        hasta_str = request.POST.get("periodo_fin", "")
        try:
            desde = _date.fromisoformat(desde_str)
            hasta = _date.fromisoformat(hasta_str)
        except ValueError:
            messages.error(request, "Fechas de período inválidas.")
            return redirect("crear_liquidacion_tesorero")

        def _dec(nombre, default=Decimal("0")):
            val = request.POST.get(nombre, "").strip().replace(",", ".")
            try:
                return Decimal(val)
            except Exception:
                return default

        recaudacion_base = _dec("recaudacion_base")
        monto_fijo       = _dec("monto_fijo")
        monto_variable   = _dec("monto_variable")
        monto_total      = monto_fijo + monto_variable
        notas            = request.POST.get("notas_tesorero", "").strip()

        estado = "comprobante_enviado" if "comprobante_pago" in request.FILES else "borrador"

        liq = LiquidacionPlataforma(
            municipio        = municipio,
            periodo_inicio   = desde,
            periodo_fin      = hasta,
            recaudacion_base = recaudacion_base,
            monto_fijo       = monto_fijo,
            monto_variable   = monto_variable,
            monto_total      = monto_total,
            iniciado_por     = "tesorero",
            notas_tesorero   = notas,
            estado           = estado,
        )
        if "comprobante_pago" in request.FILES:
            liq.comprobante_pago = request.FILES["comprobante_pago"]

        liq.save()
        label = "enviada al superadmin con comprobante adjunto" if estado == "comprobante_enviado" else "guardada como borrador"
        messages.success(request, f"Liquidación {label}.")
        return redirect("gestionar_liquidacion_plataforma", liquidacion_id=liq.id)

    # GET: calcular montos sugeridos
    import calendar
    hoy = timezone.localtime().date()
    if hoy.month == 1:
        desde_sugerido = _date(hoy.year - 1, 12, 1)
        hasta_sugerido = _date(hoy.year - 1, 12, 31)
    else:
        desde_sugerido = _date(hoy.year, hoy.month - 1, 1)
        _, ultimo_dia  = calendar.monthrange(hoy.year, hoy.month - 1)
        hasta_sugerido = _date(hoy.year, hoy.month - 1, ultimo_dia)

    # Importamos la función de cálculo del módulo superadmin para reutilizar
    from .views_superadmin import _calcular_recaudacion
    from .models import ModuloMunicipio
    recaudacion_calculada = _calcular_recaudacion(municipio, desde_sugerido, hasta_sugerido)

    # Sumar aportes de módulos activos (igual que en crear_liquidacion_plataforma)
    modulos_activos     = ModuloMunicipio.objects.filter(municipio=municipio, activo=True)
    extra_fijo          = sum(m.precio_mensual    for m in modulos_activos)
    extra_pct           = sum(m.porcentaje_modulo for m in modulos_activos)
    monto_fijo_sugerido = (municipio.cuota_mantenimiento_mensual or Decimal("0")) + extra_fijo
    porcentaje          = (municipio.porcentaje_plataforma or Decimal("0")) + extra_pct
    monto_variable_sugerido = (recaudacion_calculada * porcentaje / 100).quantize(Decimal("0.01"))

    return render(request, "tesorero/crear_liquidacion_plataforma.html", {
        "municipio":               municipio,
        "desde_sugerido":          desde_sugerido,
        "hasta_sugerido":          hasta_sugerido,
        "recaudacion_calculada":   recaudacion_calculada,
        "monto_fijo_sugerido":     monto_fijo_sugerido,
        "monto_variable_sugerido": monto_variable_sugerido,
        "monto_total_sugerido":    monto_fijo_sugerido + monto_variable_sugerido,
        "concepto":                municipio.get_concepto_recaudacion_display(),
    })


@require_role("tesorero")
def gestionar_liquidacion_plataforma(request, liquidacion_id):
    """
    El tesorero ve el detalle de una liquidación y puede:
    - Subir/reemplazar el comprobante de pago (→ comprobante_enviado)
    - Agregar notas
    """
    municipio = request.user.municipio
    liq = get_object_or_404(LiquidacionPlataforma, id=liquidacion_id, municipio=municipio)

    if request.method == "POST":
        accion = request.POST.get("accion", "")

        if accion == "subir_comprobante":
            if "comprobante_pago" not in request.FILES:
                messages.error(request, "No adjuntaste ningún comprobante.")
            elif liq.estado in ("aprobada",):
                messages.warning(request, "Esta liquidación ya fue aprobada, no se puede modificar.")
            else:
                if liq.comprobante_pago:
                    liq.comprobante_pago.delete(save=False)
                liq.comprobante_pago = request.FILES["comprobante_pago"]
                liq.notas_tesorero   = request.POST.get("notas_tesorero", liq.notas_tesorero).strip()
                liq.estado           = "comprobante_enviado"
                liq.save(update_fields=["comprobante_pago", "notas_tesorero", "estado", "actualizado_en"])
                messages.success(request, "Comprobante enviado al superadmin.")

        return redirect("gestionar_liquidacion_plataforma", liquidacion_id=liq.id)

    return render(request, "tesorero/detalle_liquidacion_plataforma.html", {
        "liq": liq,
    })
