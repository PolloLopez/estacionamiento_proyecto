# app_estacionamiento/views_inspector.py
"""
Vistas del rol Inspector.

Responsabilidades:
- Verificar vehículos en la vía pública
- Registrar infracciones
- Ver su propio resumen de caja (sin cobros)
- Generar PDF de infracciones del día

No incluye cobros ni liquidaciones (eso es responsabilidad del vendedor).
"""

from datetime import timedelta

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .decorators import require_role
from .models import (
    Estacionamiento,
    Infraccion,
    Subcuadra,
    Vehiculo,
)
from .services_infracciones import ErrorInfraccion, crear_infraccion
from .services_verificacion import verificar_estado_vehiculo
from .use_cases.finalizar_estacionamiento import ejecutar as finalizar_estacionamiento_uc
from .utils import get_subcuadra_default


# ─────────────────────────────────────────────────────────────────────────────
# Panel principal
# ─────────────────────────────────────────────────────────────────────────────

@require_role("inspector")
def panel_inspectores(request):
    """
    Panel principal del inspector.
    Muestra solo estadísticas de su actividad de verificación del día.
    No expone dinero ni cobros.
    """
    inspector = request.user
    hoy = timezone.localtime().date()

    infracciones_hoy = Infraccion.objects.filter(
        municipio=inspector.municipio,
        inspector=inspector,
        creado_en__date=hoy,
    ).count()

    resumen = {
        "infracciones_hoy": infracciones_hoy,
    }

    return render(request, "inspectores/panel_inspectores.html", {"resumen": resumen})


# ─────────────────────────────────────────────────────────────────────────────
# Verificación de vehículos
# ─────────────────────────────────────────────────────────────────────────────

@require_role("inspector")
def verificar_vehiculo(request):
    """
    Permite al inspector buscar una patente y ver su estado:
    si está estacionado, si tiene infracciones pendientes, si venció.
    Cierra automáticamente estacionamientos vencidos antes de mostrar el resultado.
    """
    resultado = None
    historial = request.session.get("historial", [])
    municipio = request.user.municipio

    modo = request.GET.get("modo", "desktop")

    # Subcuadras disponibles (el inspector elige en cuál está patrullando)
    subcuadras = Subcuadra.objects.filter(municipio=municipio).exclude(calle="Zona Única")

    # Recordar subcuadra seleccionada en sesión
    subcuadra_id = request.POST.get("subcuadra_id") or request.session.get("subcuadra_inspector_id")
    subcuadra_activa = None
    if subcuadra_id:
        try:
            subcuadra_activa = Subcuadra.objects.get(id=subcuadra_id, municipio=municipio)
            request.session["subcuadra_inspector_id"] = subcuadra_activa.id
        except Subcuadra.DoesNotExist:
            pass
    if not subcuadra_activa:
        subcuadra_activa = get_subcuadra_default(municipio)

    tipo_seleccionado = "auto"

    if request.method == "POST":
        patente = (request.POST.get("patente") or "").upper().strip()
        tipo_seleccionado = request.POST.get("tipo", "auto")

        if patente:
            # Auto-cierre de estacionamientos vencidos ANTES de verificar
            from app_estacionamiento.models import Vehiculo as VehiculoModel
            vehiculo_check = VehiculoModel.objects.filter(patente=patente).first()
            if vehiculo_check:
                est_vencido = Estacionamiento.objects.filter(
                    vehiculo=vehiculo_check, estado="ACTIVO"
                ).first()
                if est_vencido:
                    expiracion = est_vencido.hora_inicio + timedelta(
                        hours=est_vencido.duracion_horas
                    )
                    if timezone.now() >= expiracion:
                        finalizar_estacionamiento_uc(est_vencido)

                # Actualizar tipo si el inspector lo cambió y es distinto al registrado
                if vehiculo_check.tipo != tipo_seleccionado:
                    vehiculo_check.tipo = tipo_seleccionado
                    vehiculo_check.save(update_fields=["tipo"])
            else:
                # Vehículo no registrado: crearlo con el tipo indicado
                VehiculoModel.objects.create(
                    patente=patente,
                    municipio=municipio,
                    tipo=tipo_seleccionado,
                )

            resultado = verificar_estado_vehiculo(
                patente,
                request.user,
                subcuadra_activa
            )
            historial.insert(0, patente)
            request.session["historial"] = historial[:5]

    return render(request, "inspectores/verificar.html", {
        "resultado": resultado,
        "historial": historial,
        "modo": modo,
        "subcuadras": subcuadras,
        "subcuadra_activa": subcuadra_activa,
        "tipo_seleccionado": tipo_seleccionado,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Infracciones
# ─────────────────────────────────────────────────────────────────────────────

@require_role("inspector")
def registrar_infraccion(request):
    """
    Permite al inspector labrar un acta de infracción para una patente.
    Recibe la patente por GET (desde verificar_vehiculo) o POST.
    Delega la lógica de creación al service crear_infraccion().
    """
    usuario = request.user
    municipio = getattr(usuario, "municipio", None)
    if not municipio:
        return redirect("login")
    mensaje = None

    patente = request.GET.get("patente") or request.POST.get("patente")

    if not patente:
        return redirect("inspectores_verificar_vehiculo")

    vehiculo, _ = Vehiculo.objects.get_or_create(
        patente=patente,
        defaults={"municipio": usuario.municipio}
    )

    subcuadra = get_subcuadra_default(request.user.municipio)

    if not subcuadra:
        messages.error(request, "No existe subcuadra configurada.")
        return redirect("panel_inspectores")

    ultima_infraccion = Infraccion.objects.filter(inspector=usuario).order_by("-creado_en").first()
    subcuadra_default = (ultima_infraccion.subcuadra_id if ultima_infraccion else None)
    infracciones_recientes = Infraccion.objects.filter(vehiculo=vehiculo).order_by("-id")[:3]

    # Validación previa: muestra el estado actual del vehículo antes de labrar el acta
    resultado = verificar_estado_vehiculo(patente, request.user, subcuadra)

    if request.method == "POST":
        try:
            gps_lat = request.POST.get("gps_lat", "").strip() or None
            gps_lon = request.POST.get("gps_lon", "").strip() or None
            gps_acc = request.POST.get("gps_acc", "").strip() or None

            infraccion = crear_infraccion(
                patente=patente,
                subcuadra_id=request.POST.get("subcuadra_id"),
                inspector=usuario,
                foto=request.FILES.get("foto"),
                gps_lat=gps_lat,
                gps_lon=gps_lon,
                gps_acc=gps_acc,
            )

            return redirect("inspectores_ticket", infraccion.id)

        except ErrorInfraccion as e:
            mensaje = str(e)

    subcuadras = Subcuadra.objects.filter(municipio=municipio).exclude(calle="Zona Única")

    return render(request, "inspectores/registrar_infraccion.html", {
        "mensaje": mensaje,
        "vehiculo": vehiculo,
        "patente": patente,
        "subcuadra": subcuadra,
        "subcuadras": subcuadras,
        "infracciones_recientes": infracciones_recientes,
        "subcuadra_default": subcuadra_default,
        "resultado": resultado,
    })


@require_role("inspector")
def ticket_infraccion(request, infraccion_id):
    """
    Muestra el comprobante de un acta recién labrada.
    Solo accesible para el inspector del municipio.
    """
    infraccion = get_object_or_404(Infraccion, id=infraccion_id, municipio=request.user.municipio)

    return render(request, "ticket_infraccion.html", {
        "infraccion": infraccion,
    })


@require_role("inspector", "admin")
def gestion_infracciones(request):
    """
    Lista todas las infracciones del municipio.
    Accesible por inspector (su historial) y admin (gestión completa).
    """
    usuario = request.user

    infracciones = Infraccion.objects.filter(
        municipio=usuario.municipio
    ).select_related("vehiculo", "inspector").order_by("-creado_en")

    return render(request, "usuarios/historial_infracciones.html", {
        "usuario": usuario,
        "infracciones": infracciones,
        "saldo_usuario": 0,
        "tiene_pendientes": False,
        "es_vista_gestion": True,  # el template oculta los botones de pago en esta vista
    })


@require_role("inspector", "admin")
def resumen_infracciones(request):
    """
    Resumen general de infracciones del municipio para el inspector y admin.
    """
    usuario = request.user

    infracciones = Infraccion.objects.filter(
        municipio=usuario.municipio
    ).select_related("vehiculo", "subcuadra", "inspector").order_by("-creado_en")

    return render(request, "inspectores/resumen_infracciones.html", {
        "infracciones": infracciones
    })


@require_role("inspector", "admin")
def pdf_infracciones_hoy(request):
    """
    Genera y descarga un PDF con las infracciones del inspector para el día indicado.

    Parámetros:
        ?fecha=YYYY-MM-DD  (opcional, por defecto usa hoy)

    Devuelve:
        PDF adjunto con columnas: N° acta, Hora, Patente, Subcuadra, Motivo, Monto, Estado.
    """
    import io
    from datetime import date as date_type

    from django.http import HttpResponse
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Spacer, Table, TableStyle, Paragraph

    inspector = request.user

    fecha_str = request.GET.get("fecha", "")
    try:
        fecha = date_type.fromisoformat(fecha_str)
    except ValueError:
        fecha = timezone.localtime().date()

    infracciones = (
        Infraccion.objects
        .filter(inspector=inspector, municipio=inspector.municipio, creado_en__date=fecha)
        .select_related("vehiculo", "subcuadra")
        .order_by("id")
    )

    # ── Armar PDF en memoria ────────────────────────────────────────────
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
    )

    estilos = getSampleStyleSheet()
    estilo_titulo = ParagraphStyle(
        "titulo", parent=estilos["Title"], fontSize=14, alignment=TA_CENTER
    )
    estilo_sub = ParagraphStyle(
        "sub", parent=estilos["Normal"], fontSize=9, textColor=colors.HexColor("#555555")
    )

    partes = []

    municipio_nombre = inspector.municipio.nombre if inspector.municipio else ""
    partes.append(Paragraph(
        f"Infracciones del día — {fecha.strftime('%d/%m/%Y')}",
        estilo_titulo,
    ))
    partes.append(Spacer(1, 0.3*cm))
    partes.append(Paragraph(
        f"Inspector: {inspector.nombre_completo()} &nbsp;|&nbsp; Municipio: {municipio_nombre}",
        estilo_sub,
    ))
    partes.append(Spacer(1, 0.6*cm))

    ESTADOS = {"pendiente": "Pendiente", "pagada": "Pagada", "anulada": "Anulada"}
    encabezado = ["Acta", "Hora", "Patente", "Subcuadra", "Motivo", "Monto", "Estado"]
    filas = [encabezado]

    for inf in infracciones:
        hora_local = timezone.localtime(inf.creado_en).strftime("%H:%M")
        filas.append([
            str(inf.id),
            hora_local,
            inf.vehiculo.patente,
            str(inf.subcuadra.calle) if inf.subcuadra else "—",
            inf.motivo or "—",
            f"${inf.monto}",
            ESTADOS.get(inf.estado, inf.estado.capitalize()),
        ])

    if len(filas) == 1:
        partes.append(Paragraph("Sin infracciones registradas para esta fecha.", estilos["Normal"]))
    else:
        anchos = [1.5*cm, 1.5*cm, 2.2*cm, 3.5*cm, 4.5*cm, 1.8*cm, 2.2*cm]
        tabla = Table(filas, colWidths=anchos, repeatRows=1)
        tabla.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
            ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
            ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, 0), 9),
            ("FONTSIZE",      (0, 1), (-1, -1), 8),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
            ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
            ("ALIGN",         (5, 0), (5, -1), "RIGHT"),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        partes.append(tabla)

    total = len(filas) - 1
    partes.append(Spacer(1, 0.5*cm))
    partes.append(Paragraph(
        f"Total: <b>{total}</b> infracción{'es' if total != 1 else ''}",
        estilos["Normal"],
    ))

    doc.build(partes)
    buffer.seek(0)

    nombre_archivo = f"infracciones_{fecha.strftime('%Y%m%d')}_{inspector.id}.pdf"
    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{nombre_archivo}"'
    return response
