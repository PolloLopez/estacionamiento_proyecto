# app_estacionamiento/views_admin.py
"""
Vistas del rol Admin (municipio).

Responsabilidades:
- Panel y dashboard de estadísticas
- Gestión de inspectores y vendedores
- Gestión de conductores y sus datos
- Gestión de tarifas, horarios y días especiales
- Exenciones de vehículos
- Rendiciones de caja y certificación de cierres
- Verificaciones de identidad y exenciones de conductores
- Infracciones: listado, anulación, cobro en efectivo

No incluye cobros de MercadoPago (eso es views_mp.py).
"""

from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .decorators import require_role
from .services.infracciones import cobrar_infraccion_efectivo
from .services.saldo import cargar_saldo_conductor
from .utils import sanitizar_patente
from .models import (
    CierreCaja,
    DiaEspecial,
    Estacionamiento,
    HorarioEstacionamiento,
    Infraccion,
    MovimientoCaja,
    Notificacion,
    Rendicion,
    SolicitudVerificacion,
    Subcuadra,
    Tarifa,
    TIPOS_EXENCION,
    Usuario,
    Vehiculo,
    VehiculoUsuario,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helper privado
# ─────────────────────────────────────────────────────────────────────────────

def _enviar_email_verificacion(correo, nombre, aprobado, motivo=""):
    """
    Envía un email al conductor informando el resultado de su verificación.
    No lanza excepciones — un email que falla no debe interrumpir el flujo.
    """
    try:
        if aprobado:
            asunto = "✅ Tu cuenta fue verificada"
            cuerpo = (
                f"Hola {nombre},\n\n"
                "¡Buenas noticias! Tu identidad fue verificada correctamente por el municipio.\n"
                "Ya podés acceder a todas las funciones de la plataforma.\n\n"
                "Sistema de Estacionamiento"
            )
        else:
            asunto = "❌ Tu verificación fue rechazada"
            cuerpo = (
                f"Hola {nombre},\n\n"
                "Tu solicitud de verificación fue rechazada."
            )
            if motivo:
                cuerpo += f"\n\nMotivo: {motivo}"
            cuerpo += (
                "\n\nPodés volver a enviar tu solicitud desde la plataforma.\n\n"
                "Sistema de Estacionamiento"
            )
        send_mail(asunto, cuerpo, None, [correo], fail_silently=True)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Panel y dashboard
# ─────────────────────────────────────────────────────────────────────────────

@require_role("admin")
def panel_admin(request):
    """Panel principal del admin: resumen del municipio (usuarios, cobros, pendientes)."""
    usuario   = request.user
    municipio = getattr(usuario, "municipio", None)
    if not municipio:
        return redirect("login")

    inspectores = Usuario.objects.filter(es_inspector=True, municipio=municipio)
    vendedores  = Usuario.objects.filter(es_vendedor=True,  municipio=municipio)
    conductores = Usuario.objects.filter(es_conductor=True, municipio=municipio)

    infracciones_recientes = Infraccion.objects.filter(
        municipio=municipio
    ).order_by("-creado_en")[:20]

    # Sin rendir: movimientos abiertos + cierres no certificados
    abiertos = MovimientoCaja.objects.filter(
        usuario__municipio=municipio, tipo="ingreso", cerrado=False
    ).aggregate(total=Sum("monto"))["total"] or 0
    en_cierre_sin_certificar = CierreCaja.objects.filter(
        usuario__municipio=municipio, certificado=False
    ).aggregate(total=Sum("monto_municipio"))["total"] or 0
    sin_rendir = abiertos + en_cierre_sin_certificar

    verificaciones_pendientes = SolicitudVerificacion.objects.filter(
        estado="pendiente", usuario__municipio=municipio
    ).count()

    rendiciones_pendientes = CierreCaja.objects.filter(
        usuario__municipio=municipio, certificado=False,
    ).count()

    from django.urls import reverse as _reverse

    # Ítems del sidebar de gestión: label, url, badge (opcional)
    sidebar_gestion = [
        {"label": "👤 Usuarios",         "url": _reverse("gestionar_usuarios"),       "badge": None},
        {"label": "👮 Inspectores",       "url": _reverse("gestionar_inspectores"),    "badge": None},
        {"label": "💰 Vendedores",        "url": _reverse("gestionar_vendedores"),     "badge": None},
        {"label": "🚗 Vehículos",         "url": _reverse("admin_vehiculos"),          "badge": None},
        {"label": "📋 Infracciones",      "url": _reverse("admin_infracciones"),       "badge": None},
        {"label": "🚫 Exenciones",        "url": _reverse("exenciones"),               "badge": None},
        {"label": "💲 Tarifas",           "url": _reverse("gestionar_tarifas"),        "badge": None},
        {"label": "🕐 Horarios",          "url": _reverse("gestionar_horarios"),       "badge": None},
        {"label": "📅 Días especiales",   "url": _reverse("gestionar_dias_especiales"),"badge": None},
        {"label": "✅ Verificaciones",    "url": _reverse("gestionar_verificaciones"), "badge": verificaciones_pendientes or None},
        {"label": "💼 Rendiciones",       "url": _reverse("admin_rendiciones"),        "badge": rendiciones_pendientes or None},
    ]

    return render(request, "admin/panel_admin.html", {
        "inspectores":               inspectores,
        "vendedores":                vendedores,
        "conductores":               conductores,
        "infracciones_recientes":    infracciones_recientes,
        "sin_rendir":                sin_rendir,
        "verificaciones_pendientes": verificaciones_pendientes,
        "rendiciones_pendientes":    rendiciones_pendientes,
        "sidebar_gestion":           sidebar_gestion,
    })


@require_role("admin")
def dashboard_admin(request):
    """Dashboard de estadísticas: infracciones por inspector, patentes por día, cobros."""
    municipio = request.user.municipio

    infracciones_por_inspector = Infraccion.objects.filter(
        municipio=municipio
    ).values("inspector__correo").annotate(total=Count("id")).order_by("-total")

    patentes_por_dia = Vehiculo.objects.filter(
        municipio=municipio
    ).annotate(fecha=TruncDate("fecha_creacion")).values("fecha").annotate(total=Count("id"))

    cobros = MovimientoCaja.objects.filter(
        usuario__municipio=municipio
    ).values("usuario__correo").annotate(total=Sum("monto")).order_by("-total")

    return render(request, "admin/panel_admin.html", {
        "infracciones_por_inspector": infracciones_por_inspector,
        "patentes_por_dia":           patentes_por_dia,
        "cobros":                     cobros,
    })


@require_role("admin")
def inicio_admin(request):
    """Alias de entrada al admin — redirige al panel principal."""
    return redirect("panel_admin")


# ─────────────────────────────────────────────────────────────────────────────
# Exenciones de vehículos
# ─────────────────────────────────────────────────────────────────────────────

@require_role("admin")
def panel_exenciones(request):
    """
    Busca un vehículo por patente y gestiona su exención (global o parcial por subcuadra).
    Puede recibir ?patente=XYZ desde detalle_usuario para pre-cargar.
    """
    usuario   = request.user
    municipio = getattr(usuario, "municipio", None)
    if not municipio:
        return redirect("login")

    subcuadras = Subcuadra.objects.filter(municipio=municipio)
    vehiculo   = None
    accion     = request.POST.get("accion")

    def _buscar_vehiculo(patente):
        return Vehiculo.objects.filter(patente=patente).filter(
            Q(municipio=municipio) | Q(municipio__isnull=True)
        ).first()

    # Pre-carga desde detalle_usuario con ?patente=
    patente_get = sanitizar_patente(request.GET.get("patente", ""))
    if patente_get and not accion:
        vehiculo = _buscar_vehiculo(patente_get)

    if request.method == "POST":
        if accion == "buscar":
            patente  = sanitizar_patente(request.POST.get("patente") or "")
            vehiculo = _buscar_vehiculo(patente)

        elif accion == "guardar":
            patente  = sanitizar_patente(request.POST.get("patente") or "")
            vehiculo = _buscar_vehiculo(patente)

            if vehiculo:
                vehiculo.exento_global  = request.POST.get("exento_global") == "on"
                vehiculo.tipo_exencion  = request.POST.get("tipo_exencion") or None
                vehiculo.notas_exencion = request.POST.get("notas_exencion", "").strip() or None
                vehiculo.save()

                subcuadras_ids    = request.POST.getlist("subcuadras")
                subcuadras_validas = Subcuadra.objects.filter(
                    id__in=subcuadras_ids, municipio=municipio
                ).values_list("id", flat=True)
                vehiculo.subcuadras_exentas.set(subcuadras_validas)

                messages.success(request, f"✅ Exención guardada para {vehiculo.patente}.")
            else:
                messages.error(request, "No se encontró el vehículo con esa patente.")

    return render(request, "admin/exenciones.html", {
        "vehiculo":      vehiculo,
        "subcuadras":    subcuadras,
        "tipos_exencion": TIPOS_EXENCION,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Saldo de conductores
# ─────────────────────────────────────────────────────────────────────────────

@require_role("admin")
def cargar_saldo(request, usuario_id):
    """El admin carga saldo a un conductor. Registra el movimiento en la caja del admin."""
    admin   = request.user
    usuario = get_object_or_404(Usuario, id=usuario_id, municipio=admin.municipio)

    comprobante = None

    if request.method == "POST":
        monto_str = request.POST.get("monto", "")
        try:
            monto = Decimal(monto_str)
            cargar_saldo_conductor(admin=admin, conductor=usuario, monto=monto)
            # Refresca el usuario para obtener el saldo actualizado
            usuario.refresh_from_db()
            comprobante = {
                "monto":      monto,
                "saldo_nuevo": usuario.saldo,
                "fecha":      timezone.localtime(),
                "admin":      admin,
            }
        except (ValueError, Exception):
            return render(request, "admin/cargar_saldo.html", {
                "usuario": usuario,
                "error": "Monto inválido",
            })

    return render(request, "admin/cargar_saldo.html", {
        "usuario":     usuario,
        "comprobante": comprobante,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Gestión de inspectores
# ─────────────────────────────────────────────────────────────────────────────

@require_role("admin")
def gestionar_inspectores(request):
    """Lista, crea y configura inspectores del municipio."""
    usuario   = request.user
    municipio = usuario.municipio
    error     = None

    if request.method == "POST":
        nombre   = request.POST.get("nombre", "").strip()
        correo   = request.POST.get("correo", "").strip()
        password = request.POST.get("password", "").strip()

        if not correo or not password:
            error = "Correo y contraseña son obligatorios"
        elif Usuario.objects.filter(correo=correo).exists():
            error = "Ya existe un usuario con ese correo"
        else:
            try:
                porcentaje = Decimal(request.POST.get("porcentaje_ganancia", "0") or "0")
            except Exception:
                porcentaje = Decimal("0")

            inspector = Usuario.objects.create_user(
                correo=correo,
                password=password,
                municipio=municipio,
                es_inspector=True,
                es_conductor=False,
                porcentaje_ganancia=porcentaje,
                periodicidad_rendicion=request.POST.get("periodicidad_rendicion", "semanal"),
            )
            inspector.first_name    = nombre
            inspector.telefono      = request.POST.get("telefono", "").strip()
            inspector.numero_dni    = request.POST.get("numero_dni", "").strip()
            inspector.numero_legajo = request.POST.get("numero_legajo", "").strip()
            inspector.save()
            return redirect("gestionar_inspectores")

    inspectores = Usuario.objects.filter(
        es_inspector=True, municipio=municipio
    ).annotate(
        total_infracciones=Count("infraccion", distinct=True),
        total_verificaciones=Count("verificacioninspector", distinct=True),
        total_cobrado_sum=Sum(
            "movimientocaja__monto",
            filter=Q(movimientocaja__tipo="ingreso"),
        ),
    )

    return render(request, "admin/gestionar_inspectores.html", {
        "inspectores": inspectores,
        "error":       error,
    })


@require_role("admin")
def editar_inspector(request, inspector_id):
    """Edita datos personales y configuración de rendición de un inspector."""
    inspector = get_object_or_404(
        Usuario, id=inspector_id, es_inspector=True, municipio=request.user.municipio
    )

    if request.method == "POST":
        inspector.first_name    = request.POST.get("nombre", "").strip()
        inspector.is_active     = request.POST.get("activo") == "on"
        inspector.telefono      = request.POST.get("telefono", "").strip()
        inspector.numero_dni    = request.POST.get("numero_dni", "").strip()
        inspector.numero_legajo = request.POST.get("numero_legajo", "").strip()

        try:
            inspector.saldo_limite = Decimal(request.POST.get("saldo_limite", "0") or "0")
        except Exception:
            inspector.saldo_limite = 0
        try:
            inspector.porcentaje_ganancia = Decimal(
                request.POST.get("porcentaje_ganancia", "0") or "0"
            )
        except Exception:
            inspector.porcentaje_ganancia = 0

        inspector.periodicidad_rendicion = request.POST.get("periodicidad_rendicion", "semanal")
        inspector.save()
        return redirect("gestionar_inspectores")

    movimientos = MovimientoCaja.objects.filter(
        usuario=inspector
    ).order_by("-creado_en")[:20]

    return render(request, "admin/editar_inspector.html", {
        "inspector":   inspector,
        "movimientos": movimientos,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Gestión de vendedores
# ─────────────────────────────────────────────────────────────────────────────

@require_role("admin")
def gestionar_vendedores(request):
    """Lista, crea y configura vendedores (kioscos) del municipio."""
    usuario   = request.user
    municipio = usuario.municipio
    error     = None

    if request.method == "POST":
        nombre   = request.POST.get("nombre", "").strip()
        correo   = request.POST.get("correo", "").strip()
        password = request.POST.get("password", "").strip()

        if not correo or not password:
            error = "Correo y contraseña son obligatorios"
        elif Usuario.objects.filter(correo=correo).exists():
            error = "Ya existe un usuario con ese correo"
        else:
            try:
                porcentaje = Decimal(request.POST.get("porcentaje_ganancia", "0") or "0")
            except Exception:
                porcentaje = Decimal("0")

            vendedor = Usuario.objects.create_user(
                correo=correo,
                password=password,
                municipio=municipio,
                es_vendedor=True,
                es_conductor=False,
                porcentaje_ganancia=porcentaje,
                periodicidad_rendicion=request.POST.get("periodicidad_rendicion", "semanal"),
            )
            vendedor.first_name         = nombre
            vendedor.nombre_propietario = request.POST.get("nombre_propietario", "").strip()
            vendedor.documento_cuil     = request.POST.get("documento_cuil", "").strip()
            vendedor.telefono           = request.POST.get("telefono", "").strip()
            vendedor.horario_atencion   = request.POST.get("horario_atencion", "").strip()
            vendedor.save()
            return redirect("gestionar_vendedores")

    vendedores = Usuario.objects.filter(es_vendedor=True, municipio=municipio)
    return render(request, "admin/gestionar_vendedores.html", {
        "vendedores": vendedores,
        "error":      error,
    })


@require_role("admin")
def editar_vendedor(request, vendedor_id):
    """Edita datos y configuración de comisión de un vendedor."""
    vendedor = get_object_or_404(
        Usuario, id=vendedor_id, es_vendedor=True, municipio=request.user.municipio
    )

    if request.method == "POST":
        vendedor.first_name         = request.POST.get("nombre", "").strip()
        vendedor.is_active          = request.POST.get("activo") == "on"
        vendedor.nombre_propietario = request.POST.get("nombre_propietario", "").strip()
        vendedor.documento_cuil     = request.POST.get("documento_cuil", "").strip()
        vendedor.telefono           = request.POST.get("telefono", "").strip()
        vendedor.horario_atencion   = request.POST.get("horario_atencion", "").strip()
        try:
            vendedor.saldo_limite = Decimal(request.POST.get("saldo_limite", "0") or "0")
        except Exception:
            vendedor.saldo_limite = 0
        try:
            vendedor.porcentaje_ganancia = Decimal(
                request.POST.get("porcentaje_ganancia", "0") or "0"
            )
        except Exception:
            vendedor.porcentaje_ganancia = 0
        vendedor.periodicidad_rendicion = request.POST.get("periodicidad_rendicion", "semanal")
        vendedor.save()
        return redirect("gestionar_vendedores")

    return render(request, "admin/editar_vendedor.html", {"vendedor": vendedor})


# ─────────────────────────────────────────────────────────────────────────────
# Gestión de conductores
# ─────────────────────────────────────────────────────────────────────────────



@require_role("admin")
def crear_conductor(request):
    """El admin da de alta un conductor manualmente (registro presencial).

    Una vez creado, redirige al detalle para agregar vehículos y exenciones.
    """
    admin     = request.user
    municipio = admin.municipio
    error     = None

    if request.method == "POST":
        nombre   = request.POST.get("nombre", "").strip().title()
        apellido = request.POST.get("apellido", "").strip().title()
        correo   = request.POST.get("correo", "").strip().lower()
        password = request.POST.get("password", "").strip()

        if not all([nombre, apellido, correo, password]):
            error = "Todos los campos son obligatorios."
        elif len(password) < 6:
            error = "La contraseña debe tener al menos 6 caracteres."
        elif Usuario.objects.filter(correo=correo).exists():
            error = f"Ya existe un usuario con el correo {correo}."
        else:
            conductor = Usuario.objects.create_user(
                correo=correo,
                password=password,
                first_name=nombre,
                last_name=apellido,
                municipio=municipio,
                es_conductor=True,
                es_admin=False,
                es_inspector=False,
                es_vendedor=False,
            )
            messages.success(
                request,
                f"Conductor {nombre} {apellido} creado. "
                "Podés agregarle vehículo y exención desde acá."
            )
            return redirect("detalle_usuario_admin", usuario_id=conductor.id)

    return render(request, "admin/crear_conductor.html", {
        "error": error,
    })

@require_role("admin")
def gestionar_usuarios(request):
    """Lista de conductores del municipio con búsqueda por correo o nombre."""
    usuario   = request.user
    municipio = usuario.municipio

    q = request.GET.get("q", "").strip()
    usuarios = Usuario.objects.filter(
        es_conductor=True, municipio=municipio
    ).prefetch_related("vehiculos")

    if q:
        usuarios = usuarios.filter(
            Q(correo__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q)
        )

    return render(request, "admin/gestionar_usuarios.html", {
        "usuarios": usuarios,
        "q":        q,
    })


@require_role("admin")
def detalle_usuario_admin(request, usuario_id):
    """
    Detalle de un conductor: datos, vehículos, infracciones recientes.
    Permite agregar vehículos y editar datos básicos del conductor.
    """
    conductor = get_object_or_404(
        Usuario, id=usuario_id, es_conductor=True, municipio=request.user.municipio
    )
    vehiculos = Vehiculo.objects.filter(vehiculousuario__usuario=conductor)
    accion    = request.POST.get("accion") if request.method == "POST" else None

    if accion == "agregar_vehiculo":
        patente = sanitizar_patente(request.POST.get("patente") or "")
        tipo    = request.POST.get("tipo", "auto")
        if tipo not in ("auto", "moto"):
            tipo = "auto"
        if patente:
            vehiculo, creado = Vehiculo.objects.get_or_create(patente=patente)
            if creado:
                vehiculo.tipo = tipo
                vehiculo.save(update_fields=["tipo"])
            VehiculoUsuario.objects.get_or_create(usuario=conductor, vehiculo=vehiculo)
            messages.success(
                request, f"Vehículo {patente} ({vehiculo.get_tipo_display()}) agregado."
            )
            vehiculos = Vehiculo.objects.filter(vehiculousuario__usuario=conductor)

    elif accion == "editar_datos":
        nombre        = request.POST.get("nombre", "").strip()
        apellido      = request.POST.get("apellido", "").strip()
        telefono      = request.POST.get("telefono", "").strip()
        numero_dni    = request.POST.get("numero_dni", "").strip()
        es_verificado = request.POST.get("es_verificado") == "1"

        if nombre:
            conductor.first_name = nombre.title()
        if apellido:
            conductor.last_name = apellido.title()
        conductor.telefono      = telefono
        conductor.numero_dni    = numero_dni
        conductor.es_verificado = es_verificado
        conductor.save(update_fields=[
            "first_name", "last_name", "telefono", "numero_dni", "es_verificado"
        ])
        messages.success(request, "Datos actualizados.")

    # Últimas 5 infracciones (preview)
    infracciones = Infraccion.objects.filter(
        vehiculo__vehiculousuario__usuario=conductor,
        municipio=request.user.municipio,
    ).distinct().order_by("-creado_en")[:5]

    return render(request, "admin/detalle_usuario.html", {
        "conductor":   conductor,
        "vehiculos":   vehiculos,
        "infracciones": infracciones,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Infracciones (vista admin)
# ─────────────────────────────────────────────────────────────────────────────

@require_role("admin")
def admin_infracciones(request):
    """
    Lista de infracciones con filtros (patente, inspector, estado, fechas).
    Permite anular o cobrar en efectivo directamente desde la vista.
    """
    usuario   = request.user
    municipio = usuario.municipio

    infracciones = Infraccion.objects.filter(municipio=municipio).select_related(
        "vehiculo", "inspector", "subcuadra"
    ).order_by("-creado_en")

    patente      = sanitizar_patente(request.GET.get("patente", ""))
    inspector_id = request.GET.get("inspector", "").strip()
    estado       = request.GET.get("estado", "").strip()
    fecha_desde  = request.GET.get("fecha_desde", "").strip()
    fecha_hasta  = request.GET.get("fecha_hasta", "").strip()

    if patente:
        infracciones = infracciones.filter(vehiculo__patente__icontains=patente)
    if inspector_id:
        infracciones = infracciones.filter(inspector_id=inspector_id)
    if estado:
        infracciones = infracciones.filter(estado=estado)
    if fecha_desde:
        infracciones = infracciones.filter(creado_en__date__gte=fecha_desde)
    if fecha_hasta:
        infracciones = infracciones.filter(creado_en__date__lte=fecha_hasta)

    if request.method == "POST":
        accion        = request.POST.get("accion")
        infraccion_id = request.POST.get("infraccion_id")

        if accion == "anular" and infraccion_id:
            inf = get_object_or_404(Infraccion, id=infraccion_id, municipio=municipio)
            motivo_anulacion = request.POST.get("motivo_anulacion", "").strip()
            if not motivo_anulacion:
                messages.error(request, "Debés ingresar un motivo para anular la infracción.")
                return redirect(request.get_full_path() + f"#inf-{infraccion_id}")
            if inf.estado == "pendiente":
                inf.estado = "anulada"
                inf.motivo_anulacion = motivo_anulacion
                inf.save(update_fields=["estado", "motivo_anulacion"])
                messages.success(request, f"Infracción #{inf.id} anulada.")

        elif accion == "cobrar" and infraccion_id:
            inf = get_object_or_404(Infraccion, id=infraccion_id, municipio=municipio)
            try:
                inf = cobrar_infraccion_efectivo(infraccion=inf, cobrador=usuario)
            except ValueError as e:
                messages.warning(request, str(e))
                return redirect(request.get_full_path())
            except Exception as e:
                messages.error(request, f"Error al cobrar: {e}")
                return redirect(request.get_full_path())
            return redirect(reverse("ticket_pago_multa", args=[inf.id]))

        return redirect(request.get_full_path())

    inspectores = Usuario.objects.filter(municipio=municipio, es_inspector=True)

    # Permite abrir el modal de detalle al entrar con ?detalle=ID
    detalle_id = request.GET.get("detalle", "").strip()

    return render(request, "admin/infracciones.html", {
        "infracciones": infracciones[:200],
        "inspectores":  inspectores,
        "detalle_id":  detalle_id,
        "filtros": {
            "patente":     patente,
            "inspector":   inspector_id,
            "estado":      estado,
            "fecha_desde": fecha_desde,
            "fecha_hasta": fecha_hasta,
        },
    })


@require_role("admin")
def comprobante_infraccion(request, infraccion_id):
    """Vista de impresión para comprobante de pago de infracción."""
    infraccion = get_object_or_404(
        Infraccion, id=infraccion_id, municipio=request.user.municipio
    )
    return render(request, "admin/comprobante_infraccion.html", {
        "infraccion": infraccion,
        "municipio":  request.user.municipio,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Tarifas, horarios y días especiales
# ─────────────────────────────────────────────────────────────────────────────

@require_role("admin")
def gestionar_tarifas(request):
    """
    Configura tarifas y parámetros del municipio:
    precio hora (auto/moto), monto infracción, abonos, comisión vendedor, tolerancia multa.
    """
    usuario   = request.user
    municipio = usuario.municipio
    error     = None

    if request.method == "POST":
        def _decimal(campo, minimo=0):
            val = request.POST.get(campo, "0").strip() or "0"
            d   = Decimal(val)
            if d < minimo:
                raise ValueError(f"El campo '{campo}' debe ser >= {minimo}.")
            return d

        def _entero(campo, minimo=0):
            val = request.POST.get(campo, "0").strip() or "0"
            n   = int(val)
            if n < minimo:
                raise ValueError(f"El campo '{campo}' debe ser >= {minimo}.")
            return n

        try:
            precio_auto = _decimal("precio_por_hora", minimo=Decimal("0.01"))
            _val_moto   = request.POST.get("precio_por_hora_moto", "").strip()
            precio_moto = Decimal(_val_moto) if _val_moto else None
            monto_inf   = _decimal("monto_infraccion", minimo=0)
            abono_auto  = _decimal("precio_abono_auto", minimo=0)
            abono_moto  = _decimal("precio_abono_moto", minimo=0)
            comision    = _decimal("comision_vendedor", minimo=0)
            tolerancia  = _entero("tolerancia_multa_minutos", minimo=0)

            Tarifa.objects.update_or_create(
                municipio=municipio,
                defaults={
                    "precio_por_hora":      precio_auto,
                    "precio_por_hora_moto": precio_moto,
                    "monto_infraccion":     monto_inf,
                    "precio_abono_auto":    abono_auto,
                    "precio_abono_moto":    abono_moto,
                }
            )

            municipio.comision_vendedor        = comision
            municipio.tolerancia_multa_minutos = tolerancia
            municipio.save(update_fields=["comision_vendedor", "tolerancia_multa_minutos"])

            messages.success(request, "✅ Tarifas y configuración guardadas correctamente.")
            return redirect("gestionar_tarifas")

        except Exception as e:
            error = f"Error al guardar: {e}"

    tarifa_actual = Tarifa.objects.filter(municipio=municipio).first()
    return render(request, "admin/gestionar_tarifas.html", {
        "tarifa_actual": tarifa_actual,
        "municipio":     municipio,
        "error":         error,
    })


@require_role("admin")
def gestionar_horarios(request):
    """Gestión de horarios semanales de cobro por municipio."""
    municipio = request.user.municipio
    DIAS      = HorarioEstacionamiento.DIAS

    if request.method == "POST":
        for dia_num, _ in DIAS:
            activo      = request.POST.get(f"activo_{dia_num}") == "1"
            hora_inicio = request.POST.get(f"hora_inicio_{dia_num}", "").strip()
            hora_fin    = request.POST.get(f"hora_fin_{dia_num}", "").strip()

            HorarioEstacionamiento.objects.update_or_create(
                municipio=municipio,
                dia_semana=dia_num,
                defaults={
                    "hora_inicio": hora_inicio or "08:00",
                    "hora_fin":    hora_fin    or "15:00",
                    "activo":      activo and bool(hora_inicio) and bool(hora_fin),
                }
            )
        return redirect("gestionar_horarios")

    horarios_existentes = {
        h.dia_semana: h
        for h in HorarioEstacionamiento.objects.filter(municipio=municipio)
    }
    dias_con_horario = [
        (dia_num, dia_label, horarios_existentes.get(dia_num))
        for dia_num, dia_label in DIAS
    ]

    return render(request, "admin/gestionar_horarios.html", {
        "dias_con_horario": dias_con_horario,
    })


@require_role("admin")
def gestionar_dias_especiales(request):
    """Alta, baja y listado de días especiales (feriados, festivos, duelos)."""
    municipio = request.user.municipio

    if request.method == "POST":
        accion = request.POST.get("accion")

        if accion == "agregar":
            fecha        = request.POST.get("fecha", "").strip()
            tipo         = request.POST.get("tipo", "feriado")
            descripcion  = request.POST.get("descripcion", "").strip()
            cobro_activo = request.POST.get("cobro_activo") == "1"
            if fecha and descripcion:
                DiaEspecial.objects.update_or_create(
                    municipio=municipio,
                    fecha=fecha,
                    defaults={
                        "tipo":        tipo,
                        "descripcion": descripcion,
                        "cobro_activo": cobro_activo,
                    }
                )

        elif accion == "eliminar":
            dia_id = request.POST.get("dia_id")
            DiaEspecial.objects.filter(id=dia_id, municipio=municipio).delete()

        return redirect("gestionar_dias_especiales")

    dias = DiaEspecial.objects.filter(municipio=municipio).order_by("fecha")
    return render(request, "admin/gestionar_dias_especiales.html", {
        "dias":  dias,
        "tipos": DiaEspecial.TIPOS,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Rendiciones y cierres de caja
# ─────────────────────────────────────────────────────────────────────────────

@require_role("admin")
def admin_rendiciones(request):
    """
    Lista todos los cierres de caja del municipio con filtros.
    Permite filtrar por estado (pendiente/certificado), usuario y rango de fechas.
    """
    municipio = getattr(request.user, "municipio", None)

    filtro      = request.GET.get("filtro", "todos")
    usuario_id  = request.GET.get("usuario_id", "").strip()
    fecha_desde = request.GET.get("fecha_desde", "").strip()
    fecha_hasta = request.GET.get("fecha_hasta", "").strip()

    cierres = CierreCaja.objects.filter(
        usuario__municipio=municipio
    ).select_related("usuario", "certificado_por").order_by("-fecha_cierre")

    if filtro == "pendientes":
        cierres = cierres.filter(certificado=False)
    elif filtro == "certificados":
        cierres = cierres.filter(certificado=True)

    if usuario_id:
        cierres = cierres.filter(usuario_id=usuario_id)
    if fecha_desde:
        cierres = cierres.filter(fecha_cierre__date__gte=fecha_desde)
    if fecha_hasta:
        cierres = cierres.filter(fecha_cierre__date__lte=fecha_hasta)

    conteo_pendientes = CierreCaja.objects.filter(
        usuario__municipio=municipio, certificado=False,
    ).count()

    paginator = Paginator(cierres, 20)
    page_obj  = paginator.get_page(request.GET.get("page", 1))

    usuarios_con_cierres = Usuario.objects.filter(
        municipio=municipio,
        cierrecaja__isnull=False,
    ).filter(Q(es_inspector=True) | Q(es_vendedor=True)).distinct().order_by("first_name", "correo")

    # Rendiciones propias del admin a tesorería (para que vea cuáles están pendientes de validación)
    mis_rendiciones = Rendicion.objects.filter(
        admin=request.user
    ).order_by("-fecha_hasta")[:20]

    return render(request, "admin/rendiciones.html", {
        "cierres":            page_obj,
        "filtro":             filtro,
        "conteo_pendientes":  conteo_pendientes,
        "usuario_id":         usuario_id,
        "fecha_desde":        fecha_desde,
        "fecha_hasta":        fecha_hasta,
        "usuarios_con_cierres": usuarios_con_cierres,
        "page_obj":           page_obj,
        "mis_rendiciones":    mis_rendiciones,
    })


@require_role("admin")
def crear_rendicion(request):
    """
    El admin genera una rendición a tesorería con desglose efectivo/digital/comisiones.
    El total_neto = efectivo + digital − comisiones.
    """
    municipio = request.user.municipio

    if request.method == "POST":
        periodo         = request.POST.get("periodo", "").strip()
        fecha_desde_str = request.POST.get("fecha_desde", "").strip()
        fecha_hasta_str = request.POST.get("fecha_hasta", "").strip()
        notas           = request.POST.get("notas", "").strip()

        try:
            total_efectivo   = Decimal(request.POST.get("total_efectivo",   "0") or "0")
            total_digital    = Decimal(request.POST.get("total_digital",    "0") or "0")
            total_comisiones = Decimal(request.POST.get("total_comisiones", "0") or "0")
        except Exception:
            messages.error(request, "Los montos deben ser números válidos.")
            return redirect("crear_rendicion")

        if not periodo or not fecha_desde_str or not fecha_hasta_str:
            messages.error(request, "Completá todos los campos obligatorios.")
            return redirect("crear_rendicion")

        total_neto = total_efectivo + total_digital - total_comisiones

        Rendicion.objects.create(
            municipio        = municipio,
            admin            = request.user,
            periodo          = periodo,
            fecha_desde      = fecha_desde_str,
            fecha_hasta      = fecha_hasta_str,
            total_efectivo   = total_efectivo,
            total_digital    = total_digital,
            total_comisiones = total_comisiones,
            total_neto       = total_neto,
            notas_tesorero   = notas,
        )
        messages.success(request, f"Rendición generada. Total neto a rendir: ${total_neto}")
        return redirect("admin_rendiciones")

    # Sugerir fecha_desde = día siguiente a la última rendición del admin
    ultima = Rendicion.objects.filter(admin=request.user).order_by("-fecha_hasta").first()
    from datetime import timedelta
    fecha_desde_sugerida = (ultima.fecha_hasta + timedelta(days=1)) if ultima else date.today().replace(day=1)

    return render(request, "admin/crear_rendicion.html", {
        "periodos":            Rendicion.PERIODOS,
        "hoy":                 date.today(),
        "fecha_desde_sugerida": fecha_desde_sugerida,
    })


@require_role("admin")
def certificar_cierre(request, cierre_id):
    """El admin certifica (audita) un cierre de caja. Solo acepta POST."""
    cierre = get_object_or_404(
        CierreCaja.objects.select_related("usuario"),
        id=cierre_id,
        usuario__municipio=request.user.municipio,
    )

    if request.method != "POST":
        return redirect("admin_rendiciones")

    if cierre.certificado:
        messages.warning(request, "Este cierre ya estaba certificado.")
        return redirect("admin_rendiciones")

    cierre.certificado    = True
    cierre.certificado_en  = timezone.now()
    cierre.certificado_por = request.user
    cierre.save(update_fields=["certificado", "certificado_en", "certificado_por"])

    messages.success(
        request,
        f"✅ Cierre de {cierre.usuario.correo} del {cierre.fecha_cierre:%d/%m/%Y} certificado."
    )
    return redirect("admin_rendiciones")


# ─────────────────────────────────────────────────────────────────────────────
# Verificaciones de identidad y exenciones
# ─────────────────────────────────────────────────────────────────────────────

@require_role("admin")
def gestionar_verificaciones(request):
    """
    Lista solicitudes de verificación filtradas por estado.
    Pendiente muestra tanto identidades como exenciones sin resolver.
    """
    municipio     = getattr(request.user, "municipio", None)
    estado_filtro = request.GET.get("estado", "pendiente")

    solicitudes = SolicitudVerificacion.objects.select_related(
        "usuario", "vehiculo"
    ).filter(usuario__municipio=municipio)

    if estado_filtro == "pendiente":
        solicitudes = solicitudes.filter(
            Q(estado="pendiente") | Q(estado_exencion="pendiente")
        )
    elif estado_filtro in ("aprobada", "rechazada"):
        solicitudes = solicitudes.filter(estado=estado_filtro)

    conteo_pendientes = SolicitudVerificacion.objects.filter(
        estado="pendiente", usuario__municipio=municipio
    ).count()

    subcuadras = Subcuadra.objects.filter(municipio=municipio).order_by("calle", "altura")

    return render(request, "admin/gestionar_verificaciones.html", {
        "solicitudes":       solicitudes,
        "estado_filtro":     estado_filtro,
        "conteo_pendientes": conteo_pendientes,
        "subcuadras":        subcuadras,
        "tipos_exencion":    TIPOS_EXENCION,
    })


@require_role("admin")
def resolver_verificacion(request, solicitud_id):
    """
    El admin resuelve una solicitud de verificación.

    Acciones:
      aprobar           → identidad aprobada, notifica por email y app
      rechazar          → identidad rechazada + notas, notifica por email y app
      aprobar_exencion  → aplica exención global o parcial al vehículo
      rechazar_exencion → rechaza exención + notas_exencion_admin
    """
    solicitud = get_object_or_404(
        SolicitudVerificacion.objects.select_related("usuario", "vehiculo"),
        id=solicitud_id,
        usuario__municipio=request.user.municipio,
    )

    if request.method != "POST":
        return redirect("gestionar_verificaciones")

    accion = request.POST.get("accion")

    # ── Identidad ────────────────────────────────────────────────────────────
    if accion == "aprobar":
        solicitud.estado      = "aprobada"
        solicitud.notas_admin = ""
        solicitud.save(update_fields=["estado", "notas_admin"])

        solicitud.usuario.es_verificado = True
        solicitud.usuario.save(update_fields=["es_verificado"])

        messages.success(request, f"✅ Identidad aprobada: {solicitud.usuario.correo}.")

        _enviar_email_verificacion(
            correo=solicitud.usuario.correo,
            nombre=solicitud.nombre or solicitud.usuario.correo,
            aprobado=True,
        )
        Notificacion.objects.create(
            destinatario=solicitud.usuario,
            mensaje="✅ ¡Tu identidad fue verificada! El municipio confirmó tu cuenta.",
        )

    elif accion == "rechazar":
        notas                 = request.POST.get("notas_admin", "").strip()
        solicitud.estado      = "rechazada"
        solicitud.notas_admin = notas
        solicitud.save(update_fields=["estado", "notas_admin"])

        solicitud.usuario.es_verificado = False
        solicitud.usuario.save(update_fields=["es_verificado"])

        messages.warning(request, f"❌ Identidad rechazada: {solicitud.usuario.correo}.")

        _enviar_email_verificacion(
            correo=solicitud.usuario.correo,
            nombre=solicitud.nombre or solicitud.usuario.correo,
            aprobado=False,
            motivo=notas,
        )
        motivo_txt = f" Motivo: {notas}" if notas else ""
        Notificacion.objects.create(
            destinatario=solicitud.usuario,
            mensaje=f"❌ Tu verificación fue rechazada.{motivo_txt} Podés reenviar tu solicitud.",
        )

    # ── Exención ─────────────────────────────────────────────────────────────
    elif accion == "aprobar_exencion":
        vehiculo = solicitud.vehiculo
        if not vehiculo:
            messages.error(request, "La solicitud no tiene vehículo asociado.")
            return redirect("gestionar_verificaciones")

        tipo_exencion  = request.POST.get("tipo_exencion", "")
        es_global      = request.POST.get("exento_global") == "on"
        subcuadra_ids  = request.POST.getlist("subcuadras")
        notas_exencion = request.POST.get("notas_exencion", "").strip()

        vehiculo.tipo_exencion  = tipo_exencion
        vehiculo.notas_exencion = notas_exencion

        if es_global:
            vehiculo.exento_global  = True
            vehiculo.exento_parcial = False
            vehiculo.subcuadras_exentas.clear()
        else:
            vehiculo.exento_global  = False
            vehiculo.exento_parcial = bool(subcuadra_ids)
            vehiculo.subcuadras_exentas.set(subcuadra_ids)

        vehiculo.save()
        solicitud.estado_exencion = "aprobada"
        solicitud.save(update_fields=["estado_exencion"])

        tipo_label = dict(TIPOS_EXENCION).get(tipo_exencion, tipo_exencion)
        messages.success(
            request,
            f"✅ Exención '{tipo_label}' aplicada a {vehiculo.patente}."
            + (" Global." if es_global else f" {len(subcuadra_ids)} subcuadra(s)."),
        )
        Notificacion.objects.create(
            destinatario=solicitud.usuario,
            mensaje=f"✅ Tu exención fue aprobada para el vehículo {vehiculo.patente}.",
        )

    elif accion == "rechazar_exencion":
        notas_exencion_admin              = request.POST.get("notas_exencion_admin", "").strip()
        solicitud.estado_exencion         = "rechazada"
        solicitud.notas_exencion_admin    = notas_exencion_admin
        solicitud.save(update_fields=["estado_exencion", "notas_exencion_admin"])

        vehiculo_patente = solicitud.vehiculo.patente if solicitud.vehiculo else "(sin vehículo)"
        messages.warning(request, f"❌ Exención rechazada para {vehiculo_patente}.")

        motivo_txt = f" Motivo: {notas_exencion_admin}" if notas_exencion_admin else ""
        Notificacion.objects.create(
            destinatario=solicitud.usuario,
            mensaje=f"❌ Tu solicitud de exención fue rechazada.{motivo_txt}",
        )

    return redirect("gestionar_verificaciones")

# ─────────────────────────────────────────────────────────────────────────────
# Vehículos del municipio
# ─────────────────────────────────────────────────────────────────────────────

@require_role("admin")
def admin_vehiculos(request):
    """
    Lista todos los vehículos registrados en el municipio.
    Permite filtrar por patente y tipo.
    """
    municipio = request.user.municipio
    patente   = sanitizar_patente(request.GET.get("patente", ""))
    tipo      = request.GET.get("tipo", "").strip()

    vehiculos = (
        Vehiculo.objects
        .filter(municipio=municipio)
        .prefetch_related("vehiculousuario_set__usuario")
        .order_by("patente")
    )

    if patente:
        vehiculos = vehiculos.filter(patente__icontains=patente)
    if tipo:
        vehiculos = vehiculos.filter(tipo=tipo)

    paginator = Paginator(vehiculos, 50)
    page      = request.GET.get("page", 1)
    vehiculos_pag = paginator.get_page(page)

    return render(request, "admin/vehiculos.html", {
        "vehiculos": vehiculos_pag,
        "filtros": {"patente": patente, "tipo": tipo},
    })


# ─────────────────────────────────────────────────────────────────────────────
# Historial de estacionamientos del municipio
# ─────────────────────────────────────────────────────────────────────────────

@require_role("admin")
def admin_estacionamientos(request):
    """
    Historial de estacionamientos del municipio con filtros básicos.
    Útil para auditoría y para verificar el funcionamiento del sistema.
    """
    municipio   = request.user.municipio
    patente     = sanitizar_patente(request.GET.get("patente", ""))
    estado      = request.GET.get("estado", "").strip()
    fecha_desde = request.GET.get("fecha_desde", "").strip()
    fecha_hasta = request.GET.get("fecha_hasta", "").strip()

    estacionamientos = (
        Estacionamiento.objects
        .filter(subcuadra__municipio=municipio)
        .select_related("vehiculo", "usuario", "subcuadra")
        .order_by("-hora_inicio")
    )

    if patente:
        estacionamientos = estacionamientos.filter(vehiculo__patente__icontains=patente)
    if estado:
        estacionamientos = estacionamientos.filter(estado=estado)
    if fecha_desde:
        estacionamientos = estacionamientos.filter(hora_inicio__date__gte=fecha_desde)
    if fecha_hasta:
        estacionamientos = estacionamientos.filter(hora_inicio__date__lte=fecha_hasta)

    paginator = Paginator(estacionamientos, 50)
    page      = request.GET.get("page", 1)
    estacionamientos_pag = paginator.get_page(page)

    return render(request, "admin/estacionamientos.html", {
        "estacionamientos": estacionamientos_pag,
        "filtros": {
            "patente":     patente,
            "estado":      estado,
            "fecha_desde": fecha_desde,
            "fecha_hasta": fecha_hasta,
        },
    })

# ─────────────────────────────────────────────────────────────────────────────
# Vehículos del municipio
# ─────────────────────────────────────────────────────────────────────────────

@require_role("admin")
def admin_vehiculos(request):
    """
    Lista todos los vehículos registrados en el municipio.
    Permite filtrar por patente y tipo.
    """
    municipio = request.user.municipio
    patente   = sanitizar_patente(request.GET.get("patente", ""))
    tipo      = request.GET.get("tipo", "").strip()

    vehiculos = (
        Vehiculo.objects
        .filter(municipio=municipio)
        .prefetch_related("vehiculousuario_set__usuario")
        .order_by("patente")
    )

    if patente:
        vehiculos = vehiculos.filter(patente__icontains=patente)
    if tipo:
        vehiculos = vehiculos.filter(tipo=tipo)

    paginator = Paginator(vehiculos, 50)
    page      = request.GET.get("page", 1)
    vehiculos_pag = paginator.get_page(page)

    return render(request, "admin/vehiculos.html", {
        "vehiculos": vehiculos_pag,
        "filtros": {"patente": patente, "tipo": tipo},
    })


# ─────────────────────────────────────────────────────────────────────────────
# Historial de estacionamientos del municipio
# ─────────────────────────────────────────────────────────────────────────────

@require_role("admin")
def admin_estacionamientos(request):
    """
    Historial de estacionamientos del municipio con filtros básicos.
    Útil para auditoría y para verificar el funcionamiento del sistema.
    """
    municipio   = request.user.municipio
    patente     = sanitizar_patente(request.GET.get("patente", ""))
    estado      = request.GET.get("estado", "").strip()
    fecha_desde = request.GET.get("fecha_desde", "").strip()
    fecha_hasta = request.GET.get("fecha_hasta", "").strip()

    estacionamientos = (
        Estacionamiento.objects
        .filter(subcuadra__municipio=municipio)
        .select_related("vehiculo", "usuario", "subcuadra")
        .order_by("-hora_inicio")
    )

    if patente:
        estacionamientos = estacionamientos.filter(vehiculo__patente__icontains=patente)
    if estado:
        estacionamientos = estacionamientos.filter(estado=estado)
    if fecha_desde:
        estacionamientos = estacionamientos.filter(hora_inicio__date__gte=fecha_desde)
    if fecha_hasta:
        estacionamientos = estacionamientos.filter(hora_inicio__date__lte=fecha_hasta)

    paginator = Paginator(estacionamientos, 50)
    page      = request.GET.get("page", 1)
    estacionamientos_pag = paginator.get_page(page)

    return render(request, "admin/estacionamientos.html", {
        "estacionamientos": estacionamientos_pag,
        "filtros": {
            "patente":     patente,
            "estado":      estado,
            "fecha_desde": fecha_desde,
            "fecha_hasta": fecha_hasta,
        },
    })