# app_estacionamiento/views_vendedor.py
"""
Vistas del rol Vendedor (kiosco/cobrador).

Responsabilidades:
- Cobrar estacionamiento en efectivo
- Cobrar infracciones por patente
- Cobrar abono mensual
- Ver y cerrar su propia caja
- Ver y certificar sus comisiones

También incluye vistas compartidas con admin que involucran cobros:
    consultar_deuda, ticket_pago_multa, resumen_cobros, ticket_cobro.

El inspector NO tiene acceso a ninguna vista de cobro.
"""

from decimal import Decimal

from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .decorators import require_role
from .factories import EstacionamientoFactory
from .models import (
    AbonoMensual,
    CierreCaja,
    Estacionamiento,
    Infraccion,
    LiquidacionComision,
    MovimientoCaja,
    Tarifa,
    Vehiculo,
)
from .services_caja import generar_cierre_caja
from .use_cases.cobrar_estacionamiento import ejecutar as cobrar_estacionamiento
from .services.horarios import calcular_opciones_duracion, puede_estacionar_ahora
from .utils import get_subcuadra_default


# ─────────────────────────────────────────────────────────────────────────────
# Panel principal
# ─────────────────────────────────────────────────────────────────────────────

@require_role("vendedor")
def panel_vendedor(request):
    """
    Panel del vendedor: muestra totales del día, movimientos pendientes
    de cierre y comisiones acumuladas.
    """
    user = request.user
    hoy  = timezone.localdate()

    movimientos_hoy = MovimientoCaja.objects.filter(
        usuario=user, tipo="ingreso", creado_en__date=hoy,
    )
    total_hoy            = movimientos_hoy.aggregate(total=Sum("monto"))["total"] or 0
    cantidad_operaciones = movimientos_hoy.count()

    a_rendir = MovimientoCaja.objects.filter(
        usuario=user, tipo="ingreso", cerrado=False
    ).aggregate(total=Sum("monto"))["total"] or 0

    comisiones_pendientes = MovimientoCaja.objects.filter(
        usuario=user, tipo="ingreso", comision_monto__gt=0,
    ).aggregate(total=Sum("comision_monto"))["total"] or 0

    return render(request, "vendedores/panel.html", {
        "total_hoy":            total_hoy,
        "cantidad_operaciones": cantidad_operaciones,
        "a_rendir":             a_rendir,
        "comisiones_pendientes": comisiones_pendientes,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Cobro de estacionamiento
# ─────────────────────────────────────────────────────────────────────────────

@require_role("vendedor", "admin")
def registrar_estacionamiento_manual(request):
    """
    Registra un estacionamiento cobrado manualmente por el vendedor (tarifa auto).
    Valida horario del municipio y que el vehículo no esté ya activo.
    """
    vendedor   = request.user
    tarifa_obj = Tarifa.objects.filter(municipio=vendedor.municipio).first()
    tarifa_hora = tarifa_obj.precio_por_hora if tarifa_obj else Decimal("100")
    opciones_duracion = calcular_opciones_duracion(vendedor.municipio, tarifa_hora)

    def _render_form(error=None):
        return render(request, "inspectores/registrar_estacionamiento_manual.html", {
            "error": error,
            "tarifa_hora": tarifa_hora,
            "opciones_duracion": opciones_duracion,
        })

    if request.method != "POST":
        return _render_form()

    patente      = (request.POST.get("patente") or "").strip().upper()
    duracion_raw = request.POST.get("duracion")

    if not patente:
        return _render_form("Ingresá la patente del vehículo.")

    permitido, msg_horario = puede_estacionar_ahora(vendedor.municipio)
    if not permitido:
        return _render_form(msg_horario)

    try:
        duracion = Decimal(str(duracion_raw))
        if duracion <= 0 or (duracion * 2) % 1 != 0:
            raise ValueError()
    except Exception:
        return _render_form("Duración inválida. Seleccioná una opción de la lista.")

    valores_validos = [op["horas"] for op in opciones_duracion]
    if float(duracion) not in valores_validos:
        return _render_form("La duración seleccionada excede el horario de cierre.")

    vehiculo, _ = Vehiculo.objects.get_or_create(
        patente=patente, defaults={"municipio": vendedor.municipio}
    )
    if not vehiculo.municipio:
        vehiculo.municipio = vendedor.municipio
        vehiculo.save()

    if getattr(vehiculo, "exento_global", False):
        return _render_form(f"El vehículo {patente} tiene exención total — no se puede cobrar.")

    if Estacionamiento.objects.filter(vehiculo=vehiculo, estado="ACTIVO").exists():
        return _render_form("El vehículo ya tiene un estacionamiento activo.")

    subcuadra = get_subcuadra_default(vendedor.municipio)
    if not subcuadra:
        return _render_form("No hay subcuadra configurada para este municipio.")

    monto = duracion * tarifa_hora

    with transaction.atomic():
        est = EstacionamientoFactory.crear(
            usuario=vendedor,
            vehiculo=vehiculo,
            subcuadra=subcuadra,
            duracion=duracion,
            costo_base=monto,
        )
        cobrar_estacionamiento(
            inspector=vendedor,
            monto=monto,
            descripcion=f"Cobro manual {vehiculo.patente}",
        )

    return redirect(reverse("inspectores_ticket_cobro", args=[est.id]))


@require_role("vendedor", "admin")
def registrar_estacionamiento_vendedor(request):
    """
    El vendedor cobra estacionamiento en efectivo.
    Registra el ingreso en su caja y calcula su comisión.
    Respeta el horario del municipio y diferencia tarifa auto/moto.
    """
    vendedor   = request.user
    tarifa_obj = Tarifa.objects.filter(municipio=vendedor.municipio).first()

    tarifa_hora_auto = tarifa_obj.precio_por_hora if tarifa_obj else Decimal("100")
    tarifa_hora_moto = (
        tarifa_obj.precio_por_hora_moto
        if tarifa_obj and tarifa_obj.precio_por_hora_moto
        else tarifa_hora_auto
    )
    tarifa_hora       = tarifa_hora_auto
    opciones_duracion = calcular_opciones_duracion(vendedor.municipio, tarifa_hora)

    def _render_form(error=None):
        return render(request, "vendedores/registrar_estacionamiento.html", {
            "error":             error,
            "tarifa_hora":       tarifa_hora,
            "tarifa_hora_auto":  tarifa_hora_auto,
            "tarifa_hora_moto":  tarifa_hora_moto,
            "opciones_duracion": opciones_duracion,
        })

    if request.method != "POST":
        return _render_form()

    patente      = (request.POST.get("patente") or "").strip().upper()
    duracion_raw = request.POST.get("duracion")

    if not patente:
        return _render_form("Ingresá la patente del vehículo.")

    permitido, msg_horario = puede_estacionar_ahora(vendedor.municipio)
    if not permitido:
        return _render_form(msg_horario)

    try:
        duracion = Decimal(str(duracion_raw))
        if duracion <= 0 or (duracion * 2) % 1 != 0:
            raise ValueError()
    except Exception:
        return _render_form("Duración inválida.")

    vehiculo, _ = Vehiculo.objects.get_or_create(
        patente=patente, defaults={"municipio": vendedor.municipio}
    )
    if not vehiculo.municipio:
        vehiculo.municipio = vendedor.municipio
        vehiculo.save()

    if getattr(vehiculo, "exento_global", False):
        return _render_form(f"El vehículo {patente} tiene exención total — no se puede cobrar.")

    if Estacionamiento.objects.filter(vehiculo=vehiculo, estado="ACTIVO").exists():
        return _render_form("El vehículo ya tiene un estacionamiento activo.")

    subcuadra = get_subcuadra_default(vendedor.municipio)
    if not subcuadra:
        return _render_form("No hay subcuadra configurada para este municipio.")

    es_moto     = getattr(vehiculo, "tipo", "auto") == "moto"
    tarifa_cobro = tarifa_hora_moto if es_moto else tarifa_hora_auto
    monto        = duracion * tarifa_cobro

    comision_pct   = getattr(vendedor.municipio, "comision_vendedor", None) or Decimal("0")
    comision_cobro = (monto * comision_pct / 100).quantize(Decimal("0.01"))

    with transaction.atomic():
        est = EstacionamientoFactory.crear(
            usuario=vendedor,
            vehiculo=vehiculo,
            subcuadra=subcuadra,
            duracion=duracion,
            costo_base=monto,
        )
        cobrar_estacionamiento(
            inspector=vendedor,
            monto=monto,
            descripcion=f"Estacionamiento {patente}",
            comision_monto=comision_cobro,
        )

    return redirect(reverse("inspectores_ticket_cobro", args=[est.id]))


# ─────────────────────────────────────────────────────────────────────────────
# Cobro de infracciones
# ─────────────────────────────────────────────────────────────────────────────

@require_role("vendedor", "admin")
def cobrar_infraccion_vendedor(request):
    """
    El vendedor busca una patente, ve la infracción pendiente y la cobra en efectivo.
    Flujo: buscar → confirmar (modal) → cobrar.
    No valida horario — el kiosco siempre puede cobrar.
    """
    vendedor  = request.user
    municipio = vendedor.municipio
    infraccion = None
    vehiculo   = None
    patente    = ""

    if request.method == "POST":
        accion  = request.POST.get("accion")
        patente = (request.POST.get("patente") or "").strip().upper()

        if accion == "buscar" and patente:
            vehiculo = Vehiculo.objects.filter(patente=patente).filter(
                Q(municipio=municipio) | Q(municipio__isnull=True)
            ).first()

            if vehiculo:
                infraccion = Infraccion.objects.filter(
                    vehiculo=vehiculo, municipio=municipio, estado="pendiente"
                ).order_by("-creado_en").first()
                if not infraccion:
                    messages.info(request, f"El vehículo {patente} no tiene infracciones pendientes.")
            else:
                messages.warning(request, f"No se encontró el vehículo con patente {patente}.")

        elif accion == "confirmar":
            infraccion_id = request.POST.get("infraccion_id")
            patente_post  = (request.POST.get("patente") or "").strip().upper()
            if infraccion_id:
                infraccion = Infraccion.objects.filter(
                    id=infraccion_id, municipio=municipio, estado="pendiente"
                ).select_related("vehiculo", "inspector").first()
                if not infraccion:
                    messages.error(request, "Infracción no encontrada o ya procesada.")
                    return redirect("vendedores_cobrar_infraccion")
                vehiculo = infraccion.vehiculo
            return render(request, "vendedores/cobrar_infraccion.html", {
                "infraccion": infraccion,
                "vehiculo":   vehiculo,
                "patente":    patente_post,
                "confirmar":  True,
            })

        elif accion == "cobrar":
            infraccion_id = request.POST.get("infraccion_id")
            if infraccion_id:
                try:
                    with transaction.atomic():
                        inf = get_object_or_404(
                            Infraccion.objects.select_for_update(),
                            id=infraccion_id, municipio=municipio, estado="pendiente",
                        )
                        from datetime import timedelta as _td
                        tolerancia_min = municipio.tolerancia_multa_minutos or 0
                        ahora = timezone.now()
                        anulada_por_gracia = (
                            tolerancia_min > 0 and
                            (ahora - inf.creado_en) <= _td(minutes=tolerancia_min)
                        )
                        if anulada_por_gracia:
                            inf.estado = "anulada"
                        else:
                            inf.estado = "pagada"
                            comision_pct = municipio.comision_vendedor or 0
                            comision     = round(inf.monto * comision_pct / 100, 2)
                            MovimientoCaja.objects.create(
                                usuario=vendedor,
                                monto=inf.monto,
                                tipo="ingreso",
                                medio_pago="efectivo",
                                comision_monto=comision,
                                descripcion=f"Cobro infracción #{inf.id} — {inf.vehiculo.patente}",
                            )
                        inf.fecha_pago = ahora
                        inf.save()
                except Exception as e:
                    messages.error(request, f"Error al cobrar: {e}")
                    return redirect("vendedores_cobrar_infraccion")
                return redirect(reverse("ticket_pago_multa", args=[inf.id]))

    return render(request, "vendedores/cobrar_infraccion.html", {
        "infraccion": infraccion,
        "vehiculo":   vehiculo,
        "patente":    patente,
    })


@require_role("vendedor", "admin")
def cobrar_abono(request):
    """
    El vendedor cobra el abono mensual de un vehículo.

    Flujo:
    - GET / POST sin acción: formulario con patente + selector de mes
    - POST accion=confirmar: resumen antes de cobrar
    - POST accion=cobrar: registra AbonoMensual y MovimientoCaja
    """
    from datetime import date

    MESES_ES = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
    ]

    def _sumar_meses(d, n):
        """Suma n meses a la fecha d (sin dateutil)."""
        mes = d.month - 1 + n
        año = d.year + mes // 12
        mes = mes % 12 + 1
        return date(año, mes, 1)

    hoy      = date.today()
    mes_base = hoy.replace(day=1)

    opciones_mes = [
        (
            _sumar_meses(mes_base, delta).isoformat(),
            f"{MESES_ES[_sumar_meses(mes_base, delta).month - 1]} {_sumar_meses(mes_base, delta).year}",
        )
        for delta in [-2, -1, 0, 1]
    ]

    mes_str = (request.POST.get("mes") or "").strip() if request.method == "POST" else ""
    try:
        mes_seleccionado = date.fromisoformat(mes_str) if mes_str else mes_base
    except ValueError:
        mes_seleccionado = mes_base
    mes_label = f"{MESES_ES[mes_seleccionado.month - 1]} {mes_seleccionado.year}"

    vendedor   = request.user
    municipio  = vendedor.municipio
    tarifa_obj = Tarifa.objects.filter(municipio=municipio).first()

    error     = None
    vehiculo  = None
    confirmar = False
    precio    = None

    if request.method == "POST":
        accion  = request.POST.get("accion", "buscar")
        patente = (request.POST.get("patente") or "").strip().upper()

        if not patente:
            error = "Ingresá la patente del vehículo."
        else:
            vehiculo = Vehiculo.objects.filter(patente=patente).first()
            if not vehiculo:
                error = f"No existe ningún vehículo con patente {patente}."
            else:
                es_moto     = getattr(vehiculo, "tipo", "auto") == "moto"
                precio_moto = getattr(tarifa_obj, "precio_abono_moto", None) if tarifa_obj else None
                precio_auto = getattr(tarifa_obj, "precio_abono_auto", None) if tarifa_obj else None

                if es_moto and precio_moto and precio_moto > 0:
                    precio = precio_moto
                elif precio_auto and precio_auto > 0:
                    precio = precio_auto
                else:
                    error = "No hay tarifa de abono configurada. Configurala en Tarifas."

                if not error:
                    ya_tiene = AbonoMensual.objects.filter(
                        vehiculo=vehiculo, municipio=municipio, mes=mes_seleccionado,
                    ).exists()

                    if ya_tiene:
                        error = f"El vehículo {patente} ya tiene abono para {mes_label}."
                    elif accion == "confirmar":
                        confirmar = True
                    elif accion == "cobrar":
                        comision_pct   = getattr(municipio, "comision_vendedor", None) or Decimal("0")
                        comision_monto = (precio * comision_pct / 100).quantize(Decimal("0.01"))

                        with transaction.atomic():
                            movimiento = MovimientoCaja.objects.create(
                                usuario=vendedor,
                                monto=precio,
                                tipo="ingreso",
                                descripcion=f"Abono mensual {mes_seleccionado.strftime('%m/%Y')} - {patente}",
                                medio_pago="efectivo",
                                comision_monto=comision_monto,
                            )
                            AbonoMensual.objects.create(
                                vehiculo=vehiculo,
                                municipio=municipio,
                                vendedor=vendedor,
                                mes=mes_seleccionado,
                                monto=precio,
                                medio_pago="efectivo",
                                movimiento_caja=movimiento,
                            )

                        messages.success(
                            request,
                            f"Abono de {mes_label} registrado para {patente} — ${precio}. "
                            f"Comisión generada: ${comision_monto}.",
                        )
                        return redirect("cobrar_abono")

    return render(request, "vendedores/cobrar_abono.html", {
        "vehiculo":         vehiculo,
        "precio":           precio,
        "confirmar":        confirmar,
        "error":            error,
        "tarifa_obj":       tarifa_obj,
        "opciones_mes":     opciones_mes,
        "mes_seleccionado": mes_seleccionado.isoformat(),
        "mes_label":        mes_label,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Consultar deuda (compartida con admin)
# ─────────────────────────────────────────────────────────────────────────────

@require_role("admin", "vendedor")
def consultar_deuda(request):
    """
    Busca infracciones pendientes por patente y permite cobrarlas.

    Flujo:
    - GET: formulario de búsqueda
    - POST accion=confirmar: modal de confirmación
    - POST accion=cobrar: ejecuta el cobro (con tolerancia de gracia)
    """
    from django.db.models import Q as _Q

    municipio = request.user.municipio
    patente   = (request.GET.get("patente") or "").strip().upper()
    infracciones         = []
    vehiculo             = None
    infraccion_a_confirmar = None

    if patente:
        vehiculo = Vehiculo.objects.filter(patente=patente).filter(
            _Q(municipio=municipio) | _Q(municipio__isnull=True)
        ).first()
        if vehiculo:
            infracciones = Infraccion.objects.filter(
                vehiculo=vehiculo, municipio=municipio, estado="pendiente",
            ).order_by("-creado_en")

    if request.method == "POST":
        accion        = request.POST.get("accion")
        infraccion_id = request.POST.get("infraccion_id")

        if accion == "confirmar" and infraccion_id:
            patente = (request.POST.get("patente") or "").strip().upper()
            infraccion_a_confirmar = Infraccion.objects.filter(
                id=infraccion_id, municipio=municipio, estado="pendiente"
            ).select_related("vehiculo", "inspector").first()
            if not infraccion_a_confirmar:
                messages.error(request, "Infracción no encontrada o ya procesada.")
                return redirect(f"{request.path}?patente={patente}")
            if not vehiculo:
                vehiculo = Vehiculo.objects.filter(patente=patente).filter(
                    _Q(municipio=municipio) | _Q(municipio__isnull=True)
                ).first()
            if vehiculo:
                infracciones = Infraccion.objects.filter(
                    vehiculo=vehiculo, municipio=municipio, estado="pendiente"
                ).order_by("-creado_en")
            return render(request, "usuarios/consultar_deuda.html", {
                "patente":               patente,
                "vehiculo":              vehiculo,
                "infracciones":          infracciones,
                "infraccion_a_confirmar": infraccion_a_confirmar,
            })

        elif accion == "cobrar" and infraccion_id:
            try:
                with transaction.atomic():
                    inf = get_object_or_404(
                        Infraccion.objects.select_for_update(),
                        id=infraccion_id, municipio=municipio, estado="pendiente",
                    )
                    from datetime import timedelta as _td
                    tolerancia_min = municipio.tolerancia_multa_minutos or 0
                    ahora = timezone.now()
                    anulada_por_gracia = (
                        tolerancia_min > 0 and
                        (ahora - inf.creado_en) <= _td(minutes=tolerancia_min)
                    )
                    if anulada_por_gracia:
                        inf.estado = "anulada"
                    else:
                        inf.estado = "pagada"
                        comision_pct = municipio.comision_vendedor or 0
                        comision     = round(inf.monto * comision_pct / 100, 2)
                        MovimientoCaja.objects.create(
                            usuario=request.user,
                            monto=inf.monto,
                            tipo="ingreso",
                            medio_pago="efectivo",
                            comision_monto=comision,
                            descripcion=f"Cobro infracción #{inf.id} — {inf.vehiculo.patente}",
                        )
                    inf.fecha_pago = ahora
                    inf.save()
            except Exception as e:
                messages.error(request, f"Error al procesar: {e}")
                patente_param = request.POST.get("patente", "").strip().upper()
                return redirect(f"{request.path}?patente={patente_param}")
            return redirect(reverse("ticket_pago_multa", args=[inf.id]))

    return render(request, "usuarios/consultar_deuda.html", {
        "patente":               patente,
        "vehiculo":              vehiculo,
        "infracciones":          infracciones,
        "infraccion_a_confirmar": None,
    })


@require_role("admin", "vendedor")
def ticket_pago_multa(request, infraccion_id):
    """
    Comprobante de pago (o anulación por gracia) de una infracción.
    Solo se muestra si la infracción fue procesada (pagada o anulada).
    """
    infraccion = get_object_or_404(
        Infraccion, id=infraccion_id, municipio=request.user.municipio,
    )
    if infraccion.estado not in ("pagada", "anulada"):
        messages.warning(request, "Esta infracción aún está pendiente.")
        return redirect("consultar_deuda")

    return render(request, "ticket_pago_multa.html", {
        "infraccion":  infraccion,
        "cobrado_por": request.user,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Caja del vendedor
# ─────────────────────────────────────────────────────────────────────────────

@require_role("vendedor", "admin")
def caja_inspector(request):
    """
    Resumen de caja del vendedor/admin: movimientos, totales e historial de cierres.
    Nota: el nombre 'caja_inspector' se mantiene por compatibilidad con urls.py.
    El inspector NO tiene acceso — no maneja dinero.
    """
    usuario   = request.user
    municipio = getattr(usuario, "municipio", None)
    if not municipio:
        return redirect("login")

    movimientos = MovimientoCaja.objects.filter(usuario=usuario).order_by("-creado_en")

    total_ingresos     = movimientos.filter(tipo="ingreso").aggregate(total=Sum("monto"))["total"] or 0
    total_egresos      = movimientos.filter(tipo="egreso").aggregate(total=Sum("monto"))["total"] or 0
    movimientos_pendientes = movimientos.filter(tipo="ingreso", cerrado=False)
    total_a_cerrar     = movimientos_pendientes.aggregate(total=Sum("monto"))["total"] or 0

    historial_cierres = CierreCaja.objects.filter(
        usuario=usuario
    ).select_related("certificado_por").order_by("-fecha_cierre")[:20]

    return render(request, "inspectores/caja.html", {
        "movimientos":       movimientos,
        "ingresos":          total_ingresos,
        "egresos":           total_egresos,
        "saldo":             total_ingresos - total_egresos,
        "movimientos_abiertos": movimientos_pendientes.count(),
        "total_a_cerrar":    total_a_cerrar,
        "historial_cierres": historial_cierres,
    })


@require_role("vendedor", "admin")
def resumen_cobros(request):
    """Lista de todos los movimientos de caja del municipio."""
    usuario = request.user
    cobros  = MovimientoCaja.objects.filter(
        usuario__municipio=usuario.municipio
    ).select_related("usuario").order_by("-creado_en")

    return render(request, "inspectores/resumen_cobros.html", {"cobros": cobros})


@require_role("vendedor", "admin")
def ticket_cobro(request, est_id):
    """Comprobante de cobro de un estacionamiento registrado por el vendedor."""
    est = get_object_or_404(
        Estacionamiento, id=est_id, subcuadra__municipio=request.user.municipio
    )
    return render(request, "ticket.html", {
        "patente":  est.vehiculo.patente,
        "duracion": est.duracion_horas,
        "hora":     est.hora_inicio,
        "monto":    est.costo_base,
    })


@require_role("vendedor", "admin")
def resumen_caja(request):
    """Resumen detallado de caja: movimientos del día y pendientes de cierre."""
    usuario = request.user
    hoy     = timezone.localdate()

    cobros_hoy = MovimientoCaja.objects.filter(
        usuario=usuario, tipo="ingreso", creado_en__date=hoy,
    ).order_by("-creado_en")

    cobros_abiertos = MovimientoCaja.objects.filter(
        usuario=usuario, tipo="ingreso", cerrado=False,
    ).order_by("-creado_en")

    total_hoy     = cobros_hoy.aggregate(total=Sum("monto"))["total"] or 0
    total_abierto = cobros_abiertos.aggregate(total=Sum("monto"))["total"] or 0

    return render(request, "vendedores/resumen_caja.html", {
        "cobros_hoy":     cobros_hoy,
        "cobros_abiertos": cobros_abiertos,
        "total_hoy":      total_hoy,
        "total_abierto":  total_abierto,
    })


@require_role("vendedor", "admin")
def cerrar_caja(request):
    """
    Cierra la caja del vendedor: agrupa los movimientos abiertos en un CierreCaja.
    GET: muestra el resumen antes de confirmar.
    POST: ejecuta el cierre con el período seleccionado (diario/semanal/mensual).
    """
    usuario = request.user

    if request.method != "POST":
        movimientos_abiertos = MovimientoCaja.objects.filter(
            usuario=usuario, tipo="ingreso", cerrado=False
        ).order_by("creado_en")
        total_a_cerrar   = movimientos_abiertos.aggregate(total=Sum("monto"))["total"] or 0
        historial_cierres = CierreCaja.objects.filter(usuario=usuario).order_by("-fecha_cierre")[:10]

        return render(request, "inspectores/caja.html", {
            "movimientos":        MovimientoCaja.objects.filter(usuario=usuario).order_by("-creado_en"),
            "movimientos_abiertos": movimientos_abiertos.count(),
            "total_a_cerrar":     total_a_cerrar,
            "historial_cierres":  historial_cierres,
            "ingresos":           MovimientoCaja.objects.filter(usuario=usuario, tipo="ingreso").aggregate(total=Sum("monto"))["total"] or 0,
            "egresos":            MovimientoCaja.objects.filter(usuario=usuario, tipo="egreso").aggregate(total=Sum("monto"))["total"] or 0,
            "saldo":              (
                (MovimientoCaja.objects.filter(usuario=usuario, tipo="ingreso").aggregate(total=Sum("monto"))["total"] or 0)
                - (MovimientoCaja.objects.filter(usuario=usuario, tipo="egreso").aggregate(total=Sum("monto"))["total"] or 0)
            ),
            "periodos": CierreCaja.PERIODOS,
        })

    # POST — ejecutar cierre
    periodo       = request.POST.get("periodo", "").strip()
    valores_validos = [v for v, _ in CierreCaja.PERIODOS]
    if periodo and periodo not in valores_validos:
        messages.error(request, "Período no válido.")
        return redirect("panel_vendedor") if getattr(usuario, "es_vendedor", False) else redirect("inicio_admin")

    cierre = generar_cierre_caja(usuario, periodo=periodo)

    if cierre:
        periodo_label = dict(CierreCaja.PERIODOS).get(cierre.periodo, "")
        messages.success(request, f"Caja cerrada{' — ' + periodo_label if periodo_label else ''}. Total: ${cierre.total_cobrado}")
    else:
        messages.warning(request, "No había movimientos abiertos para cerrar.")

    return redirect("panel_vendedor") if getattr(usuario, "es_vendedor", False) else redirect("inicio_admin")


# ─────────────────────────────────────────────────────────────────────────────
# Comisiones del vendedor
# ─────────────────────────────────────────────────────────────────────────────

@require_role("vendedor")
def mis_comisiones(request):
    """
    El vendedor ve su historial de comisiones acumuladas y el estado
    de cada liquidación (pendiente → depositada → certificada).
    """
    vendedor  = request.user
    municipio = vendedor.municipio

    total_acumulado = MovimientoCaja.objects.filter(
        usuario=vendedor, tipo="ingreso", comision_monto__gt=0,
    ).aggregate(total=Sum("comision_monto"))["total"] or 0

    liquidaciones = LiquidacionComision.objects.filter(
        vendedor=vendedor, municipio=municipio,
    ).order_by("-creado_en")

    return render(request, "vendedores/mis_comisiones.html", {
        "total_acumulado": total_acumulado,
        "liquidaciones":   liquidaciones,
    })


@require_role("vendedor")
def certificar_comision(request, liquidacion_id):
    """
    El vendedor certifica que recibió correctamente su comisión depositada.
    Solo puede certificar liquidaciones en estado 'depositada'.
    """
    vendedor    = request.user
    liquidacion = get_object_or_404(
        LiquidacionComision, id=liquidacion_id, vendedor=vendedor,
    )

    if liquidacion.estado != "depositada":
        messages.warning(request, "Esta liquidación no está lista para certificar.")
        return redirect("mis_comisiones")

    if request.method == "POST":
        with transaction.atomic():
            liquidacion.estado         = "certificada"
            liquidacion.certificada_en = timezone.now()
            liquidacion.save(update_fields=["estado", "certificada_en"])
        messages.success(request, "Comisión certificada correctamente.")
        return redirect("mis_comisiones")

    return render(request, "vendedores/certificar_comision.html", {
        "liquidacion": liquidacion,
    })
