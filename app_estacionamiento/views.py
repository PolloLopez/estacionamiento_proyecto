# ESTACIONAMIENTO_APP/app_estacionamiento/views.py
#
# FACHADA — este archivo importa desde los módulos por rol.
# No definir vistas aquí; agregarlas en el módulo correspondiente.
#
# Módulos activos:
#   views_auth.py       → login, logout, registro, completar_perfil
#   views_inspector.py  → panel, verificar, infracciones, PDF
#   views_tesorero.py   → panel tesorero, depositar comisión
#   views_vendedor.py   → cobros, caja, comisiones
#   views_conductor.py  → estacionar, historial, infracciones propias, vehículos
#
# Próximos módulos (pendiente):
#   views_admin.py, views_mp.py

# ─── Re-exportaciones por módulo ─────────────────────────────────────────────
from .views_auth import (
    home,
    redirect_por_rol,
    inicio,
    login_view,
    registro_view,
    completar_perfil,
    logout_view,
)
from .views_inspector import (
    panel_inspectores,
    verificar_vehiculo,
    registrar_infraccion,
    ticket_infraccion,
    gestion_infracciones,
    resumen_infracciones,
    pdf_infracciones_hoy,
)
from .views_tesorero import (
    panel_tesorero,
    depositar_comision,
)
from .views_vendedor import (
    panel_vendedor,
    caja_inspector,
    consultar_deuda,
    ticket_pago_multa,
    registrar_estacionamiento_manual,
    registrar_estacionamiento_vendedor,
    resumen_cobros,
    ticket_cobro,
    cobrar_abono,
    resumen_caja,
    cobrar_infraccion_vendedor,
    cerrar_caja,
    mis_comisiones,
    certificar_comision,
)
from .views_conductor import (
    inicio_usuarios,
    marcar_notificacion_leida,
    solicitar_verificacion,
    pagar_infraccion,
    agregar_vehiculo,
    eliminar_vehiculo,
    estacionar_vehiculo,
    historial_estacionamientos,
    renovar_estacionamiento,
    finalizar_estacionamiento,
    mis_infracciones,
    simular_pago,
)
# ─────────────────────────────────────────────────────────────────────────────

import logging
logger = logging.getLogger(__name__)

from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.contrib.auth import authenticate, login, logout
from django.urls import reverse
from decimal import Decimal
from django.db import IntegrityError, transaction
from app_estacionamiento.use_cases.pagar_infraccion import ejecutar as pagar_infraccion_uc
from app_estacionamiento.services_caja import generar_cierre_caja
from app_estacionamiento.use_cases.cobrar_estacionamiento import ejecutar as cobrar_estacionamiento
from app_estacionamiento.use_cases.estacionar_vehiculo import ejecutar_estacionamiento
from .decorators import require_role, require_login
from .forms import RegistroUsuarioForm
from django.conf import settings
from django.contrib.auth.decorators import login_required
from .models import (
    Usuario,
    Vehiculo,
    VehiculoUsuario,
    Subcuadra,
    Estacionamiento,
    Infraccion,
    Municipio,
    MovimientoCaja,
    CierreCaja,
    Estado,
    VerificacionInspector,
    HorarioEstacionamiento,
    DiaEspecial,
    SolicitudVerificacion,
    Notificacion,
    AbonoMensual,
    Rendicion,
    LiquidacionComision,
    TIPOS_EXENCION,
)

from .utils import (
    get_subcuadra_default,
    puede_estacionar_ahora,
    calcular_opciones_duracion,
    cerrar_estacionamientos_vencidos_por_horario,
)
from .factories import EstacionamientoFactory
from datetime import timedelta
from django.db.models import Count, Sum, Q
from django.db.models.functions import TruncDate
from app_estacionamiento.services_verificacion import verificar_estado_vehiculo
from app_estacionamiento.services_infracciones import crear_infraccion, ErrorInfraccion
from app_estacionamiento.use_cases.finalizar_estacionamiento import ( ejecutar as finalizar_estacionamiento_uc)
from django.core.mail import send_mail


# ─── Helpers internos ─────────────────────────────────────────────────────────

def _enviar_email_verificacion(correo, nombre, aprobado, motivo=""):
    """
    Envía un email al conductor informando el resultado de su verificación.
    Si el backend es consola (sin SMTP configurado), lo imprime en el log.
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
        pass  # No interrumpir el flujo si el email falla


# =========================================================
# VIEWS ADMIN
# =========================================================
@require_role("admin")
def panel_admin(request):

    usuario = request.user
    municipio = getattr(usuario, "municipio", None)
    if not municipio:
        return redirect("login")

    inspectores = Usuario.objects.filter(es_inspector=True, municipio=municipio)
    vendedores  = Usuario.objects.filter(es_vendedor=True, municipio=municipio)
    conductores = Usuario.objects.filter(es_conductor=True, municipio=municipio)

    infracciones_recientes = Infraccion.objects.filter(
        municipio=municipio
    ).order_by("-creado_en")[:5]

    total_cobrado = MovimientoCaja.objects.filter(
        usuario__municipio=municipio,
        tipo="ingreso"
    ).aggregate(total=Sum("monto"))["total"] or 0

    verificaciones_pendientes = SolicitudVerificacion.objects.filter(
        estado="pendiente",
        usuario__municipio=municipio
    ).count()

    rendiciones_pendientes = CierreCaja.objects.filter(
        usuario__municipio=municipio,
        certificado=False,
    ).count()

    return render(request, "admin/panel_admin.html", {
        "inspectores": inspectores,
        "vendedores": vendedores,
        "conductores": conductores,
        "infracciones_recientes": infracciones_recientes,
        "total_cobrado": total_cobrado,
        "verificaciones_pendientes": verificaciones_pendientes,
        "rendiciones_pendientes": rendiciones_pendientes,
    })

@require_role("admin")
def dashboard_admin(request):
    municipio = request.user.municipio

    # 🚨 Infracciones por inspector (filtrado por municipio)
    infracciones_por_inspector = Infraccion.objects.filter(
        municipio=municipio
    ).values(
        "inspector__correo"
    ).annotate(
        total=Count("id")
    ).order_by("-total")

    # 🚗 Patentes por día (filtrado por municipio)
    patentes_por_dia = Vehiculo.objects.filter(
        municipio=municipio
    ).annotate(
        fecha=TruncDate("fecha_creacion")
    ).values("fecha").annotate(
        total=Count("id")
    )

    # 💰 Cobros por usuario (filtrado por municipio)
    cobros = MovimientoCaja.objects.filter(
        usuario__municipio=municipio
    ).values(
        "usuario__correo"
    ).annotate(
        total=Sum("monto")
    ).order_by("-total")

    return render(request, "admin/panel_admin.html", {
        "infracciones_por_inspector": infracciones_por_inspector,
        "patentes_por_dia": patentes_por_dia,
        "cobros": cobros
    })

@require_role("admin")
def panel_exenciones(request):
    usuario = request.user

    municipio = getattr(usuario, "municipio", None)

    if not municipio:
        return redirect("login")

    subcuadras = Subcuadra.objects.filter(municipio=municipio)

    # Inicializamos vehiculo en None para evitar NameError en GET
    vehiculo = None
    accion = request.POST.get("accion")

    def _buscar_vehiculo(patente):
        """Busca vehículo por patente dentro del municipio (o sin municipio asignado)."""
        return Vehiculo.objects.filter(
            patente=patente
        ).filter(
            Q(municipio=municipio) | Q(municipio__isnull=True)
        ).first()

    # Si viene ?patente=XYZ desde detalle_usuario, pre-buscamos el vehículo
    patente_get = request.GET.get("patente", "").strip().upper()
    if patente_get and not accion:
        vehiculo = _buscar_vehiculo(patente_get)

    # 🔎 BUSCAR
    if request.method == "POST" and accion == "buscar":
        patente = (request.POST.get('patente') or "").strip().upper()
        vehiculo = _buscar_vehiculo(patente)

    # 💾 GUARDAR
    elif request.method == "POST" and accion == "guardar":
        patente = (request.POST.get('patente') or "").strip().upper()
        vehiculo = _buscar_vehiculo(patente)

        if vehiculo:
            vehiculo.exento_global = request.POST.get("exento_global") == "on"
            vehiculo.tipo_exencion = request.POST.get("tipo_exencion") or None
            vehiculo.notas_exencion = request.POST.get("notas_exencion", "").strip() or None
            vehiculo.save()

            subcuadras_ids = request.POST.getlist("subcuadras")
            subcuadras_validas = Subcuadra.objects.filter(
                id__in=subcuadras_ids,
                municipio=municipio
            ).values_list("id", flat=True)
            vehiculo.subcuadras_exentas.set(subcuadras_validas)

            messages.success(request, f"✅ Exención guardada para {vehiculo.patente}.")
        else:
            messages.error(request, "No se encontró el vehículo con esa patente.")

    return render(request, "admin/exenciones.html", {
        "vehiculo": vehiculo,
        "subcuadras": subcuadras,
        "tipos_exencion": TIPOS_EXENCION,
    })

@require_role("admin")
def cargar_saldo(request, usuario_id):
    admin = request.user
    usuario = get_object_or_404(Usuario, id=usuario_id, municipio=admin.municipio)

    if request.method == "POST":
        monto = request.POST.get("monto")
        try:
            monto = Decimal(monto)
            if monto <= 0:
                raise ValueError()

            with transaction.atomic():
                usuario.saldo += monto
                usuario.save()

                # Registro de auditoría: quién cargó, a quién, cuánto
                MovimientoCaja.objects.create(
                    usuario=admin,
                    monto=monto,
                    tipo="ingreso",
                    descripcion=f"Carga de saldo para {usuario.correo} por {admin.correo}"
                )

            messages.success(request, f"Saldo de ${monto} cargado correctamente.")
            return redirect("panel_admin")

        except (ValueError, Exception):
            return render(request, "admin/cargar_saldo.html", {
                "usuario": usuario,
                "error": "Monto inválido"
            })

    return render(request, "admin/cargar_saldo.html", {"usuario": usuario})

# =========================================================
# VIEWS GESTIÓN ADMIN
# =========================================================

@require_role("admin")
def inicio_admin(request):
    # Esta vista no se usa — redirigir al panel principal
    return redirect("panel_admin")

@require_role("admin")
def gestionar_inspectores(request):
    usuario = request.user
    municipio = usuario.municipio
    error = None

    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        correo = request.POST.get("correo", "").strip()
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
            inspector.first_name       = nombre
            inspector.telefono         = request.POST.get("telefono", "").strip()
            inspector.numero_dni       = request.POST.get("numero_dni", "").strip()
            inspector.numero_legajo    = request.POST.get("numero_legajo", "").strip()
            inspector.save()
            return redirect("gestionar_inspectores")

    # Anotar stats por inspector para mostrar en resumen
    inspectores = Usuario.objects.filter(
        es_inspector=True, municipio=municipio
    ).annotate(
        total_infracciones=Count("infraccion", distinct=True),
        total_verificaciones=Count("verificacioninspector", distinct=True),
        total_cobrado_sum=Sum(
            "movimientocaja__monto",
            filter=Q(movimientocaja__tipo="ingreso")
        ),
    )

    return render(request, "admin/gestionar_inspectores.html", {
        "inspectores": inspectores,
        "error": error,
    })

@require_role("admin")
def editar_inspector(request, inspector_id):
    inspector = get_object_or_404(Usuario, id=inspector_id, es_inspector=True, municipio=request.user.municipio)

    if request.method == "POST":
        inspector.first_name    = request.POST.get("nombre", "").strip()
        inspector.is_active     = request.POST.get("activo") == "on"
        inspector.telefono      = request.POST.get("telefono", "").strip()
        inspector.numero_dni    = request.POST.get("numero_dni", "").strip()
        inspector.numero_legajo = request.POST.get("numero_legajo", "").strip()

        # Configuración de rendición
        try:
            inspector.saldo_limite = Decimal(request.POST.get("saldo_limite", "0") or "0")
        except Exception:
            inspector.saldo_limite = 0
        try:
            inspector.porcentaje_ganancia = Decimal(request.POST.get("porcentaje_ganancia", "0") or "0")
        except Exception:
            inspector.porcentaje_ganancia = 0
        inspector.periodicidad_rendicion = request.POST.get("periodicidad_rendicion", "semanal")

        inspector.save()
        return redirect("gestionar_inspectores")

    # Últimos 20 movimientos de caja del inspector
    movimientos = MovimientoCaja.objects.filter(
        usuario=inspector
    ).order_by("-creado_en")[:20]

    return render(request, "admin/editar_inspector.html", {
        "inspector": inspector,
        "movimientos": movimientos,
    })

@require_role("admin")
def gestionar_vendedores(request):
    usuario = request.user
    municipio = usuario.municipio
    error = None

    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        correo = request.POST.get("correo", "").strip()
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
            vendedor.first_name          = nombre
            vendedor.nombre_propietario  = request.POST.get("nombre_propietario", "").strip()
            vendedor.documento_cuil      = request.POST.get("documento_cuil", "").strip()
            vendedor.telefono            = request.POST.get("telefono", "").strip()
            vendedor.horario_atencion    = request.POST.get("horario_atencion", "").strip()
            vendedor.save()
            return redirect("gestionar_vendedores")

    vendedores = Usuario.objects.filter(es_vendedor=True, municipio=municipio)
    return render(request, "admin/gestionar_vendedores.html", {
        "vendedores": vendedores,
        "error": error,
    })

@require_role("admin")
def editar_vendedor(request, vendedor_id):
    vendedor = get_object_or_404(Usuario, id=vendedor_id, es_vendedor=True, municipio=request.user.municipio)

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
            vendedor.porcentaje_ganancia = Decimal(request.POST.get("porcentaje_ganancia", "0") or "0")
        except Exception:
            vendedor.porcentaje_ganancia = 0
        vendedor.periodicidad_rendicion = request.POST.get("periodicidad_rendicion", "semanal")
        vendedor.save()
        return redirect("gestionar_vendedores")

    return render(request, "admin/editar_vendedor.html", {
        "vendedor": vendedor,
    })

@require_role("admin")
def gestionar_usuarios(request):
    usuario = request.user
    municipio = usuario.municipio

    # Búsqueda: por correo (incluye gmail de OAuth) o por nombre
    q = request.GET.get("q", "").strip()
    usuarios = Usuario.objects.filter(es_conductor=True, municipio=municipio).prefetch_related("vehiculos")

    if q:
        from django.db.models import Q as QueryQ
        usuarios = usuarios.filter(
            QueryQ(correo__icontains=q) | QueryQ(first_name__icontains=q) | QueryQ(last_name__icontains=q)
        )

    return render(request, "admin/gestionar_usuarios.html", {
        "usuarios": usuarios,
        "q": q,
    })

@require_role("admin")
def detalle_usuario_admin(request, usuario_id):
    """Vista de detalle de un conductor: datos, saldo, vehículos, exenciones, historial infracciones."""
    conductor = get_object_or_404(Usuario, id=usuario_id, es_conductor=True, municipio=request.user.municipio)
    vehiculos = Vehiculo.objects.filter(vehiculousuario__usuario=conductor)

    accion = request.POST.get("accion") if request.method == "POST" else None

    # Agregar vehículo desde admin
    if accion == "agregar_vehiculo":
        patente = (request.POST.get("patente") or "").strip().upper()
        tipo    = request.POST.get("tipo", "auto")
        if tipo not in ("auto", "moto"):
            tipo = "auto"
        if patente:
            vehiculo, creado = Vehiculo.objects.get_or_create(patente=patente)
            if creado:
                vehiculo.tipo = tipo
                vehiculo.save(update_fields=["tipo"])
            VehiculoUsuario.objects.get_or_create(usuario=conductor, vehiculo=vehiculo)
            messages.success(request, f"Vehículo {patente} ({vehiculo.get_tipo_display()}) agregado.")
            vehiculos = Vehiculo.objects.filter(vehiculousuario__usuario=conductor)

    # Editar datos del conductor
    elif accion == "editar_datos":
        nombre        = request.POST.get("nombre", "").strip()
        apellido      = request.POST.get("apellido", "").strip()
        telefono      = request.POST.get("telefono", "").strip()
        numero_dni    = request.POST.get("numero_dni", "").strip()
        es_verificado = request.POST.get("es_verificado") == "1"

        if nombre:
            conductor.first_name = nombre
        if apellido:
            conductor.last_name = apellido
        conductor.telefono      = telefono
        conductor.numero_dni    = numero_dni
        conductor.es_verificado = es_verificado
        conductor.save(update_fields=["first_name", "last_name", "telefono", "numero_dni", "es_verificado"])
        messages.success(request, "Datos actualizados.")

    # Últimas 5 infracciones de sus vehículos (preview — "Ver todas" va a admin_infracciones)
    infracciones = Infraccion.objects.filter(
        vehiculo__vehiculousuario__usuario=conductor,
        municipio=request.user.municipio,
    ).distinct().order_by("-creado_en")[:5]

    return render(request, "admin/detalle_usuario.html", {
        "conductor": conductor,
        "vehiculos": vehiculos,
        "infracciones": infracciones,
    })

@require_role("admin")
def admin_infracciones(request):
    """Lista de infracciones con filtros: patente, inspector, estado, fecha."""
    usuario = request.user
    municipio = usuario.municipio

    infracciones = Infraccion.objects.filter(municipio=municipio).select_related(
        "vehiculo", "inspector", "subcuadra"
    ).order_by("-creado_en")

    # Filtros GET
    patente = request.GET.get("patente", "").strip().upper()
    inspector_id = request.GET.get("inspector", "").strip()
    estado = request.GET.get("estado", "").strip()
    fecha_desde = request.GET.get("fecha_desde", "").strip()
    fecha_hasta = request.GET.get("fecha_hasta", "").strip()

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

    # Acciones POST: anular o cobrar infracción
    if request.method == "POST":
        accion = request.POST.get("accion")
        infraccion_id = request.POST.get("infraccion_id")

        if accion == "anular" and infraccion_id:
            inf = get_object_or_404(Infraccion, id=infraccion_id, municipio=municipio)
            if inf.estado == "pendiente":
                inf.estado = "anulada"
                inf.save()
                messages.success(request, f"Infracción #{inf.id} anulada.")

        elif accion == "cobrar" and infraccion_id:
            try:
                with transaction.atomic():
                    # select_for_update bloquea la fila — si dos admins cobran
                    # la misma infraccion al mismo tiempo, el segundo espera y
                    # luego falla por estado != pendiente
                    inf = get_object_or_404(
                        Infraccion.objects.select_for_update(),
                        id=infraccion_id,
                        municipio=municipio,
                    )
                    if inf.estado != "pendiente":
                        messages.warning(request, f"La infraccion #{inf.id} ya fue procesada.")
                        return redirect(request.get_full_path())
                    inf.estado = "pagada"
                    inf.fecha_pago = timezone.now()
                    inf.save()
                    # Registrar ingreso en caja de quien cobro
                    comision_pct = municipio.comision_vendedor or 0
                    comision = round(inf.monto * comision_pct / 100, 2)
                    MovimientoCaja.objects.create(
                        usuario=usuario,
                        monto=inf.monto,
                        tipo="ingreso",
                        medio_pago="efectivo",
                        comision_monto=comision,
                        descripcion=f"Cobro en efectivo infraccion #{inf.id} — {inf.vehiculo.patente}",
                    )
            except Exception as e:
                messages.error(request, f"Error al cobrar: {e}")
                return redirect(request.get_full_path())
            # Redirigir al comprobante (no agregar messages aqui — el comprobante es la confirmacion)
            return redirect(reverse("ticket_pago_multa", args=[inf.id]))

        return redirect(request.get_full_path())

    inspectores = Usuario.objects.filter(municipio=municipio, es_inspector=True)

    return render(request, "admin/infracciones.html", {
        "infracciones": infracciones[:200],  # limitar para performance
        "inspectores": inspectores,
        "filtros": {
            "patente": patente,
            "inspector": inspector_id,
            "estado": estado,
            "fecha_desde": fecha_desde,
            "fecha_hasta": fecha_hasta,
        },
    })


@require_role("admin")
def gestionar_tarifas(request):
    """
    Gestiona tarifas de estacionamiento y configuración del municipio.

    Permite configurar:
    - Precio por hora (auto y moto)
    - Monto de infracción
    - Precios de abono mensual (auto y moto)
    - Comisión de vendedor (%)
    - Tolerancia de multa (minutos)
    """
    usuario = request.user
    municipio = usuario.municipio
    from app_estacionamiento.models import Tarifa

    error = None
    if request.method == "POST":
        def _decimal(campo, minimo=0):
            val = request.POST.get(campo, "0").strip() or "0"
            d = Decimal(val)
            if d < minimo:
                raise ValueError(f"El campo '{campo}' debe ser mayor o igual a {minimo}.")
            return d

        def _entero(campo, minimo=0):
            val = request.POST.get(campo, "0").strip() or "0"
            n = int(val)
            if n < minimo:
                raise ValueError(f"El campo '{campo}' debe ser >= {minimo}.")
            return n

        try:
            precio_auto  = _decimal("precio_por_hora", minimo=Decimal("0.01"))
            # precio_moto vacío = None → usa tarifa de auto
            _val_moto = request.POST.get("precio_por_hora_moto", "").strip()
            precio_moto = Decimal(_val_moto) if _val_moto else None
            monto_inf    = _decimal("monto_infraccion", minimo=0)
            abono_auto   = _decimal("precio_abono_auto", minimo=0)
            abono_moto   = _decimal("precio_abono_moto", minimo=0)
            comision     = _decimal("comision_vendedor", minimo=0)
            tolerancia   = _entero("tolerancia_multa_minutos", minimo=0)

            # Guardar tarifas
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

            # Guardar configuración del municipio
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
    DIAS = HorarioEstacionamiento.DIAS

    if request.method == "POST":
        for dia_num, dia_label in DIAS:
            activo = request.POST.get(f"activo_{dia_num}") == "1"
            hora_inicio = request.POST.get(f"hora_inicio_{dia_num}", "").strip()
            hora_fin = request.POST.get(f"hora_fin_{dia_num}", "").strip()

            if activo and hora_inicio and hora_fin:
                HorarioEstacionamiento.objects.update_or_create(
                    municipio=municipio,
                    dia_semana=dia_num,
                    defaults={
                        "hora_inicio": hora_inicio,
                        "hora_fin": hora_fin,
                        "activo": True,
                    }
                )
            else:
                # Si no está activo, guardar igual pero marcado como inactivo
                HorarioEstacionamiento.objects.update_or_create(
                    municipio=municipio,
                    dia_semana=dia_num,
                    defaults={"activo": False,
                              "hora_inicio": hora_inicio or "08:00",
                              "hora_fin": hora_fin or "15:00"}
                )
        return redirect("gestionar_horarios")

    # Construir dict {dia_num: horario_o_None}
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
            fecha      = request.POST.get("fecha", "").strip()
            tipo       = request.POST.get("tipo", "feriado")
            descripcion = request.POST.get("descripcion", "").strip()
            cobro_activo = request.POST.get("cobro_activo") == "1"
            if fecha and descripcion:
                DiaEspecial.objects.update_or_create(
                    municipio=municipio,
                    fecha=fecha,
                    defaults={
                        "tipo": tipo,
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
        "dias": dias,
        "tipos": DiaEspecial.TIPOS,
    })


@require_role("admin")
def comprobante_infraccion(request, infraccion_id):
    """Vista de impresión para comprobante de pago de infracción."""
    infraccion = get_object_or_404(
        Infraccion, id=infraccion_id, municipio=request.user.municipio
    )
    return render(request, "admin/comprobante_infraccion.html", {
        "infraccion": infraccion,
        "municipio": request.user.municipio,
    })


# =========================================================
# VIEWS LOGIN / LOGOUT
# =========================================================
# =========================================================
# =========================================================
# VIEWS MERCADOPAGO - CARGA DE SALDO
# =========================================================

@require_login
def mp_iniciar_carga(request):
    """
    Paso 1: el conductor elige el monto y se crea una preferencia en MercadoPago.
    MP devuelve una URL de checkout a la que redirigimos al usuario.
    """
    import mercadopago

    if request.method != "POST":
        return render(request, "usuarios/mp_cargar_saldo.html", {
            "montos_rapidos": [500, 1000, 2000, 5000],
        })

    monto_str = request.POST.get("monto", "")
    try:
        monto = int(monto_str)
        if monto <= 0:
            raise ValueError()
    except (ValueError, TypeError):
        messages.error(request, "Ingresa un monto valido mayor a 0.")
        return render(request, "usuarios/mp_cargar_saldo.html")

    access_token = settings.MP_ACCESS_TOKEN
    if not access_token:
        messages.error(request, "MercadoPago no esta configurado en este entorno.")
        return render(request, "usuarios/mp_cargar_saldo.html")

    sdk = mercadopago.SDK(access_token)

    # La URL base del sitio (necesaria para los callbacks de MP)
    # En Railway, el proxy termina el SSL y puede no pasar HTTP_X_FORWARDED_PROTO
    # en tiempo de procesar MP. Forzamos HTTPS en producción para que MP acepte
    # las back_urls (auto_return requiere HTTPS obligatoriamente).
    base_url = request.build_absolute_uri("/").rstrip("/")
    if not settings.DEBUG:
        base_url = base_url.replace("http://", "https://")

    preferencia = {
        "items": [
            {
                "title": "Carga de saldo - Estacionamiento",
                "quantity": 1,
                "unit_price": float(monto),
                "currency_id": "ARS",
            }
        ],
        "back_urls": {
            "success": f"{base_url}/usuarios/mp/exitoso/",
            "failure": f"{base_url}/usuarios/mp/fallido/",
            "pending": f"{base_url}/usuarios/mp/pendiente/",
        },
        # auto_return eliminado: requería back_urls en HTTPS estricto y daba
        # error 400 "auto_return invalid". El webhook + back_urls alcanzan.
        # El webhook recibe notificaciones de MP (asincrono)
        "notification_url": f"{base_url}/usuarios/mp/webhook/",
        # Metadatos para identificar al usuario en el webhook
        "metadata": {
            "usuario_id": str(request.user.id),
            "monto": str(monto),
        },
        "external_reference": f"usuario_{request.user.id}_monto_{monto}",
    }

    resultado = sdk.preference().create(preferencia)

    if resultado["status"] not in (200, 201):
        # Loguear el error completo de MP para diagnóstico en Railway logs
        logger.error(
            "MercadoPago error al crear preferencia | status=%s | response=%s | usuario=%s",
            resultado.get("status"),
            resultado.get("response"),
            request.user.id,
        )
        # Mostrar detalle del error en DEBUG para facilitar diagnóstico
        if settings.DEBUG:
            detalle = resultado.get("response", {})
            messages.error(request, f"Error MP ({resultado.get('status')}): {detalle}")
        else:
            messages.error(request, "No se pudo crear la preferencia de pago. Revisá los logs del servidor.")
        return render(request, "usuarios/mp_cargar_saldo.html", {
            "montos_rapidos": [500, 1000, 2000, 5000],
        })

    respuesta_mp = resultado["response"]

    # Detectar si el request viene de un dispositivo mobile.
    # En mobile usamos mobile_init_point: abre la app de MercadoPago si está instalada,
    # y cae al browser como fallback. En desktop usamos init_point (web).
    user_agent = request.META.get("HTTP_USER_AGENT", "").lower()
    es_mobile = any(kw in user_agent for kw in (
        "android", "iphone", "ipad", "ipod", "mobile", "blackberry", "windows phone"
    ))

    if settings.MP_SANDBOX:
        # Sandbox: solo tiene sandbox_init_point (sin mobile)
        checkout_url = respuesta_mp.get("sandbox_init_point", "")
    elif es_mobile and respuesta_mp.get("mobile_init_point"):
        # Producción mobile: abre la app de MercadoPago si está instalada
        checkout_url = respuesta_mp["mobile_init_point"]
    else:
        # Producción desktop
        checkout_url = respuesta_mp.get("init_point", "")

    if not checkout_url:
        messages.error(request, "No se pudo obtener la URL de pago de MercadoPago.")
        return render(request, "usuarios/mp_cargar_saldo.html", {
            "montos_rapidos": [500, 1000, 2000, 5000],
        })

    return redirect(checkout_url)


@require_login
def mp_exitoso(request):
    """
    MP redirige aquí después de un pago aprobado.

    SEGURIDAD: NO confiamos en los parámetros GET (monto, estado).
    Consultamos la API de MP con el payment_id para obtener el monto real.
    El webhook también acredita de forma asíncrona como respaldo.
    """
    import mercadopago
    from decimal import Decimal
    from app_estacionamiento.use_cases.acreditar_saldo_mp import ejecutar as acreditar

    payment_id = request.GET.get("payment_id", "").strip()

    if not payment_id:
        messages.warning(request, "No se recibió confirmación del pago.")
        return render(request, "usuarios/mp_resultado.html", {"estado": "fallido"})

    # Verificar el pago directamente con la API de MP
    try:
        sdk = mercadopago.SDK(settings.MP_ACCESS_TOKEN)
        resultado = sdk.payment().get(payment_id)

        if resultado["status"] != 200:
            raise Exception("MP no devolvió el pago")

        info = resultado["response"]

        if info.get("status") != "approved":
            messages.warning(request, "El pago aún no fue acreditado por MercadoPago.")
            return render(request, "usuarios/mp_resultado.html", {"estado": "pendiente"})

        # Verificar que el pago le pertenece a este usuario
        metadata = info.get("metadata", {})
        usuario_id_mp = str(metadata.get("usuario_id", ""))
        if usuario_id_mp and usuario_id_mp != str(request.user.id):
            # El pago no corresponde a este usuario — no acreditar
            messages.error(request, "Error de validación del pago.")
            return render(request, "usuarios/mp_resultado.html", {"estado": "fallido"})

        # Monto real desde la API (no desde la URL)
        monto = Decimal(str(info.get("transaction_amount", 0)))
        if monto <= 0:
            raise Exception("Monto inválido en la respuesta de MP")

    except Exception as e:
        # Si falla la verificación, el webhook igual acreditará
        messages.warning(
            request,
            "Tu pago fue procesado. Si no ves el saldo en unos minutos, contactá soporte."
        )
        return render(request, "usuarios/mp_resultado.html", {"estado": "pendiente"})

    try:
        acreditar(request.user, monto, payment_id)
    except Exception:
        # Si ya fue acreditado por el webhook, esta bien
        pass

    # Refrescar saldo desde la DB y redirigir al inicio con mensaje
    request.user.refresh_from_db()
    messages.success(request, f"✅ Se acreditaron ${monto} a tu saldo. Nuevo saldo: ${request.user.saldo}")
    return redirect("inicio_usuarios")


@require_login
def mp_fallido(request):
    messages.error(request, "El pago fue rechazado o cancelado. No se realizó ningún cobro.")
    return redirect("mp_iniciar_carga")


@require_login
def mp_pendiente(request):
    messages.warning(request, "El pago está siendo procesado. El saldo se acreditará automáticamente cuando se confirme.")
    return redirect("inicio_usuarios")


from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse

@csrf_exempt
def mp_webhook(request):
    """
    Webhook que MercadoPago llama de forma asincrona para notificar pagos.
    Se ejecuta independientemente de que el usuario haya vuelto al sitio o no.
    Esto garantiza que el saldo se acredite aunque el usuario cierre el browser.
    """
    import json
    from decimal import Decimal
    from app_estacionamiento.use_cases.acreditar_saldo_mp import ejecutar as acreditar

    if request.method != "POST":
        return HttpResponse(status=200)

    try:
        data = json.loads(request.body)
    except Exception:
        return HttpResponse(status=200)

    # MP envia tipo "payment" para pagos
    if data.get("type") != "payment":
        return HttpResponse(status=200)

    payment_id = str(data.get("data", {}).get("id", ""))
    if not payment_id:
        return HttpResponse(status=200)

    # Consultamos el detalle del pago a la API de MP
    import mercadopago
    sdk = mercadopago.SDK(settings.MP_ACCESS_TOKEN)
    pago = sdk.payment().get(payment_id)

    if pago["status"] != 200:
        return HttpResponse(status=200)

    info = pago["response"]

    if info.get("status") != "approved":
        return HttpResponse(status=200)

    # Recuperamos usuario desde metadata y monto desde transaction_amount (más seguro)
    try:
        metadata = info.get("metadata", {})
        usuario_id = metadata.get("usuario_id")
        # Usar transaction_amount (monto real procesado por MP) en vez del metadata
        # (por consistencia con mp_exitoso y para resistir cambios de promociones de MP)
        monto = Decimal(str(info.get("transaction_amount", metadata.get("monto", 0))))
        usuario = Usuario.objects.get(pk=usuario_id)
    except Exception:
        return HttpResponse(status=200)

    try:
        acreditar(usuario, monto, payment_id)
    except Exception:
        pass  # Si ya fue acreditado (idempotencia) no hay problema

    return HttpResponse(status=200)


# =========================================================
# =========================================================
# ADMIN — RENDICIONES (CIERRES DE CAJA)
# =========================================================

@require_role("admin")
def admin_rendiciones(request):
    """
    Lista todos los cierres de caja del municipio.
    El admin puede filtrar por estado, usuario, y rango de fechas.
    """
    from django.core.paginator import Paginator

    municipio = getattr(request.user, "municipio", None)

    # Filtros GET
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
        usuario__municipio=municipio,
        certificado=False,
    ).count()

    # Paginación
    paginator = Paginator(cierres, 20)
    page_num  = request.GET.get("page", 1)
    page_obj  = paginator.get_page(page_num)

    # Usuarios con cierres (para el selector de filtro)
    usuarios_con_cierres = Usuario.objects.filter(
        municipio=municipio,
        cierrecaja__isnull=False,
    ).filter(
        Q(es_inspector=True) | Q(es_vendedor=True)
    ).distinct().order_by("first_name", "correo")

    return render(request, "admin/rendiciones.html", {
        "cierres": page_obj,
        "filtro": filtro,
        "conteo_pendientes": conteo_pendientes,
        "usuario_id": usuario_id,
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
        "usuarios_con_cierres": usuarios_con_cierres,
        "page_obj": page_obj,
    })


@require_role("admin")
def crear_rendicion(request):
    """
    El admin genera una rendición a tesorería.
    Ingresa el período, fechas y el desglose de cobros (efectivo vs. digital).
    El total_neto se calcula automáticamente: efectivo + digital - comisiones.
    """
    from decimal import Decimal as _Dec
    from datetime import date

    municipio = request.user.municipio

    if request.method == "POST":
        periodo         = request.POST.get("periodo", "").strip()
        fecha_desde_str = request.POST.get("fecha_desde", "").strip()
        fecha_hasta_str = request.POST.get("fecha_hasta", "").strip()
        notas           = request.POST.get("notas", "").strip()

        try:
            total_efectivo   = _Dec(request.POST.get("total_efectivo", "0") or "0")
            total_digital    = _Dec(request.POST.get("total_digital",  "0") or "0")
            total_comisiones = _Dec(request.POST.get("total_comisiones", "0") or "0")
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

    return render(request, "admin/crear_rendicion.html", {
        "periodos": Rendicion.PERIODOS,
        "hoy": date.today(),
    })


@require_role("admin")
def certificar_cierre(request, cierre_id):
    """
    El admin certifica (audita) un cierre de caja.
    Solo acepta POST. Marca el cierre como certificado.
    """
    from django.utils import timezone as tz

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

    cierre.certificado = True
    cierre.certificado_en = tz.now()
    cierre.certificado_por = request.user
    cierre.save(update_fields=["certificado", "certificado_en", "certificado_por"])

    messages.success(
        request,
        f"✅ Cierre de {cierre.usuario.correo} del {cierre.fecha_cierre:%d/%m/%Y} certificado."
    )
    return redirect("admin_rendiciones")


# =========================================================
# ADMIN — VERIFICACIONES DE CONDUCTORES
# =========================================================

@require_role("admin")
def gestionar_verificaciones(request):
    """
    Lista todas las solicitudes de verificación.
    El admin puede filtrar por estado (pendiente / aprobada / rechazada).
    """
    municipio     = getattr(request.user, "municipio", None)
    estado_filtro = request.GET.get("estado", "pendiente")

    solicitudes = SolicitudVerificacion.objects.select_related(
        "usuario", "vehiculo"
    ).filter(usuario__municipio=municipio)

    if estado_filtro == "pendiente":
        # Incluir solicitudes con identidad pendiente O exención pendiente (aunque la identidad ya esté aprobada)
        solicitudes = solicitudes.filter(
            Q(estado="pendiente") | Q(estado_exencion="pendiente")
        )
    elif estado_filtro in ("aprobada", "rechazada"):
        solicitudes = solicitudes.filter(estado=estado_filtro)

    conteo_pendientes = SolicitudVerificacion.objects.filter(
        estado="pendiente",
        usuario__municipio=municipio
    ).count()

    # Subcuadras del municipio para el selector de exención parcial
    subcuadras = Subcuadra.objects.filter(municipio=municipio).order_by("calle", "altura")

    return render(request, "admin/gestionar_verificaciones.html", {
        "solicitudes": solicitudes,
        "estado_filtro": estado_filtro,
        "conteo_pendientes": conteo_pendientes,
        "subcuadras": subcuadras,
        "tipos_exencion": TIPOS_EXENCION,
    })


@require_role("admin")
def resolver_verificacion(request, solicitud_id):
    """
    El admin resuelve una solicitud de verificación.

    Acciones disponibles (campo 'accion' en POST):
      aprobar          → identidad aprobada → usuario.es_verificado=True
      rechazar         → identidad rechazada + notas_admin
      aprobar_exencion → aplica exención al vehículo según tipo y subcuadras elegidas
      rechazar_exencion → marca exención rechazada + notas_exencion_admin
    """
    solicitud = get_object_or_404(
        SolicitudVerificacion.objects.select_related("usuario", "vehiculo"),
        id=solicitud_id,
        usuario__municipio=request.user.municipio,
    )

    if request.method != "POST":
        return redirect("gestionar_verificaciones")

    accion = request.POST.get("accion")

    # ── Identidad ─────────────────────────────────────────────────────────────
    if accion == "aprobar":
        solicitud.estado = "aprobada"
        solicitud.notas_admin = ""
        solicitud.save(update_fields=["estado", "notas_admin"])

        solicitud.usuario.es_verificado = True
        solicitud.usuario.save(update_fields=["es_verificado"])

        messages.success(request, f"✅ Identidad aprobada: {solicitud.usuario.correo}.")

        # 📧 Notificar al conductor por email
        _enviar_email_verificacion(
            correo=solicitud.usuario.correo,
            nombre=solicitud.nombre or solicitud.usuario.correo,
            aprobado=True,
        )

        # 🔔 Notificación en la app
        Notificacion.objects.create(
            destinatario=solicitud.usuario,
            mensaje="✅ ¡Tu identidad fue verificada! El municipio confirmó tu cuenta.",
        )

    elif accion == "rechazar":
        notas = request.POST.get("notas_admin", "").strip()
        solicitud.estado = "rechazada"
        solicitud.notas_admin = notas
        solicitud.save(update_fields=["estado", "notas_admin"])

        solicitud.usuario.es_verificado = False
        solicitud.usuario.save(update_fields=["es_verificado"])

        messages.warning(request, f"❌ Identidad rechazada: {solicitud.usuario.correo}.")

        # 📧 Notificar al conductor por email
        _enviar_email_verificacion(
            correo=solicitud.usuario.correo,
            nombre=solicitud.nombre or solicitud.usuario.correo,
            aprobado=False,
            motivo=notas,
        )

        # 🔔 Notificación en la app
        motivo_texto = f" Motivo: {notas}" if notas else ""
        Notificacion.objects.create(
            destinatario=solicitud.usuario,
            mensaje=f"❌ Tu verificación fue rechazada.{motivo_texto} Podés reenviar tu solicitud.",
        )

    # ── Exención ──────────────────────────────────────────────────────────────
    elif accion == "aprobar_exencion":
        vehiculo = solicitud.vehiculo
        if not vehiculo:
            messages.error(request, "La solicitud no tiene vehículo asociado.")
            return redirect("gestionar_verificaciones")

        tipo_exencion = request.POST.get("tipo_exencion", "")
        es_global = request.POST.get("exento_global") == "on"
        subcuadra_ids = request.POST.getlist("subcuadras")
        notas_exencion = request.POST.get("notas_exencion", "").strip()

        vehiculo.tipo_exencion = tipo_exencion
        vehiculo.notas_exencion = notas_exencion

        if es_global:
            vehiculo.exento_global = True
            vehiculo.exento_parcial = False
            vehiculo.subcuadras_exentas.clear()
        else:
            vehiculo.exento_global = False
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
        notas_exencion_admin = request.POST.get("notas_exencion_admin", "").strip()
        solicitud.estado_exencion = "rechazada"
        solicitud.notas_exencion_admin = notas_exencion_admin
        solicitud.save(update_fields=["estado_exencion", "notas_exencion_admin"])

        vehiculo_patente = solicitud.vehiculo.patente if solicitud.vehiculo else "(sin vehículo)"
        messages.warning(request, f"❌ Exención rechazada para {vehiculo_patente}.")

        motivo_texto = f" Motivo: {notas_exencion_admin}" if notas_exencion_admin else ""
        Notificacion.objects.create(
            destinatario=solicitud.usuario,
            mensaje=f"❌ Tu solicitud de exención fue rechazada.{motivo_texto}",
        )

    return redirect("gestionar_verificaciones")


# =============================================================================
# 🏦 TESORERÍA — Panel, Rendición, Liquidaciones de comisión
# =============================================================================
