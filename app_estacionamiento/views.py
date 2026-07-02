# ESTACIONAMIENTO_APP/app_estacionamiento/views.py

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

from .utils import get_subcuadra_default
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


@require_role("inspector", "admin", "conductor", "vendedor")
def inicio_usuarios(request):
    usuario = request.user

    estacionamiento_activo = Estacionamiento.objects.filter(
        usuario=usuario,
        estado="ACTIVO"
    ).order_by("-hora_inicio").first()

    # Auto-cierre: si el tiempo pago ya venció, finalizar automáticamente
    if estacionamiento_activo:
        expiracion = estacionamiento_activo.hora_inicio + timedelta(
            hours=estacionamiento_activo.duracion_horas
        )
        if timezone.now() >= expiracion:
            finalizar_estacionamiento_uc(estacionamiento_activo)
            estacionamiento_activo = None
            messages.info(
                request,
                "⏰ Tu estacionamiento finalizó automáticamente porque venció el tiempo pago."
            )

    # Cerrar estacionamientos activos si el horario del municipio ya terminó
    if usuario.municipio:
        cerrar_estacionamientos_vencidos_por_horario(usuario.municipio)

    # Notificaciones no leídas (ej: resultado de verificación de identidad)
    notificaciones_nuevas = Notificacion.objects.filter(
        destinatario=usuario, leida=False
    ).order_by("-fecha")

    # Estado de verificación: None si no existe solicitud
    solicitud_verificacion = getattr(usuario, "solicitud_verificacion", None)

    # Abonos mensuales activos del conductor para el mes en curso
    from datetime import date
    mes_actual = date.today().replace(day=1)
    abonos_activos = AbonoMensual.objects.filter(
        vehiculo__vehiculousuario__usuario=usuario,
        municipio=usuario.municipio,
        mes=mes_actual,
    ).select_related("vehiculo").distinct() if usuario.municipio else []

    return render(request, "usuarios/inicio_usuarios.html", {
        "usuario": usuario,
        "estacionamiento_activo": estacionamiento_activo,
        "solicitud_verificacion": solicitud_verificacion,
        "notificaciones_nuevas": notificaciones_nuevas,
        "abonos_activos": abonos_activos,
    })

# =========================================================
# VIEWS USUARIOS
# =========================================================

@require_login
def marcar_notificacion_leida(request, notif_id):
    """
    Marca una notificación como leída cuando el conductor presiona 'Entendido'.
    Solo acepta POST para evitar que se marque por error con un GET.
    """
    if request.method == "POST":
        Notificacion.objects.filter(
            id=notif_id, destinatario=request.user
        ).update(leida=True)
    return redirect("inicio_usuarios")


def home(request):
    if not request.user.is_authenticated:
        return redirect("login")

    return redirect("inicio")

def redirect_por_rol(usuario):

    if usuario.es_admin:
        return redirect("panel_admin")

    elif usuario.es_inspector:
        return redirect("panel_inspectores")

    elif usuario.es_vendedor:
        return redirect("panel_vendedor")

    elif usuario.es_conductor:
        return redirect("inicio_usuarios")  # ✅ CORRECTO

    return redirect("login")

@login_required
def inicio(request):

    return redirect_por_rol(request.user)

def login_view(request):
    if request.method == "POST":
        correo = request.POST.get("correo")
        password = request.POST.get("password")

        usuario = authenticate(request, username=correo, password=password)

        if usuario is not None:
            login(request, usuario)

            # 🔥 REDIRECCIÓN POR ROL (CLAVE)
            return redirect_por_rol(usuario)

        return render(request, "usuarios/login.html", {
            "form": {"errors": True}
        })

    return render(request, "usuarios/login.html")

def registro_view(request):
    if request.method == "POST":
        form = RegistroUsuarioForm(request.POST)

        if form.is_valid():
            usuario = form.save(commit=False)

            # 🏛️ Municipio: tomar del POST si hay más de uno, sino el primero
            municipio_id = request.POST.get("municipio_id")
            if municipio_id:
                usuario.municipio = Municipio.objects.filter(id=municipio_id).first()
            else:
                usuario.municipio = Municipio.objects.first()

            usuario.save()

            # 🔐 Login automático
            login(request, usuario)

            # 🔥 REDIRECCIÓN POR ROL
            return redirect_por_rol(usuario)

    else:
        form = RegistroUsuarioForm()

    return render(request, "usuarios/registro.html", {
            "form": form,
            "municipios": Municipio.objects.filter(activo=True),
        })

@require_role("conductor")
def solicitar_verificacion(request):
    """
    El conductor envía una solicitud de verificación de identidad y,
    opcionalmente, una solicitud de exención (discapacidad o frentista).

    Flujo de identidad:
      - Si la solicitud está aprobada → solo lectura, sin reenvío.
      - Si está pendiente → muestra estado.
      - Si está rechazada o no existe → puede enviar/reenviar.

    Flujo de exención (dentro de la misma solicitud):
      - Marcando "Solicito exención" aparecen: tipo, vehículo y documentos.
      - discapacidad  → documento_1 = CUD
      - frentista     → documento_1 = licencia, documento_2 = cédula de domicilio
    """
    usuario = request.user

    try:
        solicitud = usuario.solicitud_verificacion
    except SolicitudVerificacion.DoesNotExist:
        solicitud = None

    # Vehículos registrados del conductor para el selector de exención
    vehiculos_usuario = Vehiculo.objects.filter(
        vehiculousuario__usuario=usuario
    )

    if request.method == "POST":
        if usuario.es_verificado:
            messages.error(request, "Tu cuenta ya está verificada.")
            return redirect("inicio_usuarios")

        nombre   = request.POST.get("nombre", "").strip()
        apellido = request.POST.get("apellido", "").strip()
        dni      = request.POST.get("dni", "").strip()
        telefono = request.POST.get("telefono", "").strip()

        if not nombre or not apellido or not dni:
            messages.error(request, "Nombre, apellido y DNI son obligatorios.")
            return render(request, "usuarios/solicitar_verificacion.html", {
                "solicitud": solicitud,
                "vehiculos": vehiculos_usuario,
            })

        # ── Datos de exención (opcionales) ─────────────────────────────────
        solicita_exencion     = request.POST.get("solicita_exencion") == "on"
        tipo_exencion_sol     = request.POST.get("tipo_exencion_solicitado", "").strip()
        vehiculo_id           = request.POST.get("vehiculo_id", "").strip()

        vehiculo_obj = None
        if solicita_exencion and vehiculo_id:
            vehiculo_obj = Vehiculo.objects.filter(
                id=vehiculo_id,
                vehiculousuario__usuario=usuario
            ).first()

        # Validar docs según tipo de exención
        doc1 = request.FILES.get("documento_1")
        doc2 = request.FILES.get("documento_2")

        if solicita_exencion:
            if not tipo_exencion_sol:
                messages.error(request, "Seleccioná el tipo de exención.")
                return render(request, "usuarios/solicitar_verificacion.html", {
                    "solicitud": solicitud, "vehiculos": vehiculos_usuario,
                })
            if not vehiculo_obj:
                messages.error(request, "Seleccioná el vehículo para la exención.")
                return render(request, "usuarios/solicitar_verificacion.html", {
                    "solicitud": solicitud, "vehiculos": vehiculos_usuario,
                })
            if not doc1 and not (solicitud and solicitud.documento_1):
                messages.error(request, "Adjuntá el documento principal requerido.")
                return render(request, "usuarios/solicitar_verificacion.html", {
                    "solicitud": solicitud, "vehiculos": vehiculos_usuario,
                })
            if tipo_exencion_sol == "vecino_frentista" and not doc2 and not (solicitud and solicitud.documento_2):
                messages.error(request, "La exención de frentista requiere la cédula de domicilio.")
                return render(request, "usuarios/solicitar_verificacion.html", {
                    "solicitud": solicitud, "vehiculos": vehiculos_usuario,
                })

        # ── Crear o actualizar la solicitud ──────────────────────────────────
        if solicitud:
            solicitud.nombre   = nombre
            solicitud.apellido = apellido
            solicitud.dni      = dni
            solicitud.telefono = telefono
            solicitud.estado   = "pendiente"
            solicitud.notas_admin = ""

            # Actualizar exención
            solicitud.solicita_exencion     = solicita_exencion
            solicitud.tipo_exencion_solicitado = tipo_exencion_sol if solicita_exencion else ""
            solicitud.vehiculo              = vehiculo_obj if solicita_exencion else None

            if solicita_exencion:
                # Resetear estado de exención al reenviar
                solicitud.estado_exencion    = "pendiente"
                solicitud.notas_exencion_admin = ""
                if doc1:
                    solicitud.documento_1 = doc1
                if doc2:
                    solicitud.documento_2 = doc2
            else:
                solicitud.estado_exencion = ""
                solicitud.documento_1 = None
                solicitud.documento_2 = None

            solicitud.save()
        else:
            kwargs = dict(
                usuario=usuario,
                nombre=nombre,
                apellido=apellido,
                dni=dni,
                telefono=telefono,
                solicita_exencion=solicita_exencion,
            )
            if solicita_exencion:
                kwargs["tipo_exencion_solicitado"] = tipo_exencion_sol
                kwargs["vehiculo"]                = vehiculo_obj
                kwargs["estado_exencion"]         = "pendiente"
                if doc1:
                    kwargs["documento_1"] = doc1
                if doc2:
                    kwargs["documento_2"] = doc2

            solicitud = SolicitudVerificacion.objects.create(**kwargs)

        messages.success(request, "¡Solicitud enviada! El admin la revisará a la brevedad.")
        return redirect("inicio_usuarios")

    return render(request, "usuarios/solicitar_verificacion.html", {
        "solicitud": solicitud,
        "vehiculos": vehiculos_usuario,
    })


@login_required
def completar_perfil(request):
    """
    Muestra un formulario para que el usuario seleccione su municipio.

    Se usa cuando el usuario se registró via Google OAuth en un sistema
    con múltiples municipios y aún no tiene municipio asignado.

    Una vez que selecciona, se redirige a su panel según el rol.
    """
    municipios = Municipio.objects.filter(activo=True)

    if request.method == "POST":
        municipio_id = request.POST.get("municipio_id")
        municipio = Municipio.objects.filter(id=municipio_id, activo=True).first()

        if not municipio:
            messages.error(request, "Seleccioná un municipio válido.")
            return render(request, "usuarios/completar_perfil.html", {"municipios": municipios})

        request.user.municipio = municipio
        request.user.save(update_fields=["municipio"])

        messages.success(request, f"¡Bienvenido/a! Tu municipio fue configurado como {municipio.nombre}.")
        return redirect_por_rol(request.user)

    return render(request, "usuarios/completar_perfil.html", {"municipios": municipios})


@require_login
def pagar_infraccion(request, infraccion_id):
    # Solo conductores pagan sus propias infracciones con saldo.
    # Verificamos que la patente de la infracción esté vinculada a este usuario.
    infraccion = get_object_or_404(
        Infraccion,
        id=infraccion_id,
        municipio=request.user.municipio,
        vehiculo__vehiculousuario__usuario=request.user,  # seguridad: solo sus patentes
    )
    if request.method != "POST":
        return redirect("mis_infracciones")
    try:
        pagar_infraccion_uc(request.user, infraccion)
        messages.success(request, f"✅ Infracción #{infraccion.id} pagada con tu saldo.")
    except Exception as e:
        messages.error(request, str(e))
    return redirect("mis_infracciones")

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
    vendedores = Usuario.objects.filter(es_vendedor=True, municipio=municipio)
    usuarios = Usuario.objects.filter(es_conductor=True, municipio=municipio)

    rol = request.GET.get("rol")

    estacionamientos = Estacionamiento.objects.select_related(
        "vehiculo", "subcuadra", "usuario"
    ).filter(subcuadra__municipio=municipio)


    if rol == "vendedor":
        estacionamientos = estacionamientos.filter(usuario__in=vendedores)
    elif rol == "inspector":
        estacionamientos = estacionamientos.filter(usuario__in=inspectores)
    elif rol == "conductor":
        estacionamientos = estacionamientos.filter(usuario__in=usuarios)

    estacionamientos = estacionamientos.order_by("-hora_inicio")

    # Paginación de estacionamientos
    from django.core.paginator import Paginator
    paginator_est  = Paginator(estacionamientos, 25)
    page_est       = request.GET.get("page", 1)
    estacionamientos_page = paginator_est.get_page(page_est)

    estacionamientos_activos = Estacionamiento.objects.filter(
        estado=Estado.ACTIVO,
        subcuadra__municipio=municipio
    ).count()

    infracciones_recientes = Infraccion.objects.filter(
        subcuadra__municipio=municipio
    ).order_by('-creado_en')[:5]

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
        "usuarios": usuarios,
        "estacionamientos": estacionamientos_page,
        "page_obj": estacionamientos_page,
        "estacionamientos_activos": estacionamientos_activos,
        "infracciones_recientes": infracciones_recientes,
        "rol_seleccionado": rol,
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
# VIEWS USUARIOS - CONDUCTORES
# =========================================================
@login_required
def agregar_vehiculo(request):
    """El conductor agrega un vehículo a su cuenta."""
    if request.method == "POST":
        patente = request.POST.get("patente", "").strip().upper()
        tipo    = request.POST.get("tipo", "auto")

        if tipo not in ("auto", "moto"):
            tipo = "auto"

        if not patente:
            return redirect("inicio")

        vehiculo, creado = Vehiculo.objects.get_or_create(patente=patente)

        # Si el vehículo es nuevo, asignar el tipo seleccionado
        if creado:
            vehiculo.tipo = tipo
            vehiculo.save(update_fields=["tipo"])

        VehiculoUsuario.objects.get_or_create(
            usuario=request.user,
            vehiculo=vehiculo
        )

        return redirect(
            reverse("usuarios_estacionar_vehiculo")
            + f"?patente={vehiculo.patente}"
        )

    return render(request, "usuarios/agregar_vehiculo.html")


@require_login
def eliminar_vehiculo(request, vehiculo_id):
    """El conductor desvincula un vehículo de su cuenta (no lo elimina del sistema)."""
    if request.method == "POST":
        VehiculoUsuario.objects.filter(
            usuario=request.user,
            vehiculo_id=vehiculo_id
        ).delete()
    return redirect("usuarios_estacionar_vehiculo")


def puede_estacionar_ahora(municipio):
    """
    Verifica si el horario del municipio permite estacionar en este momento.
    Tiene en cuenta días especiales (feriados, etc.) y el horario semanal.
    Retorna (permitido: bool, mensaje_error: str|None)

    Usa caché de 1 hora para no repetir queries por cada verificación.
    La clave incluye municipio + hora exacta, así cambia sola al cambiar el tramo.
    """
    from django.core.cache import cache
    from app_estacionamiento.models import HorarioEstacionamiento, DiaEspecial

    ahora       = timezone.localtime()
    hoy_fecha   = ahora.date()
    hoy_dia     = ahora.weekday()   # 0=Lunes … 6=Domingo
    hora_actual = ahora.time()

    # Clave única por municipio + hora (precisión de 1 hora)
    cache_key = f"puede_estacionar_{municipio.id}_{hoy_fecha}_{ahora.hour}"
    resultado_cached = cache.get(cache_key)
    if resultado_cached is not None:
        return resultado_cached

    # 1. Día especial sin cobro activo → libre de estacionamiento
    dia_especial = DiaEspecial.objects.filter(
        municipio=municipio, fecha=hoy_fecha
    ).first()
    if dia_especial and not dia_especial.cobro_activo:
        resultado = (False, f"Hoy es {dia_especial.descripcion}. No hay cobro de estacionamiento.")
        cache.set(cache_key, resultado, timeout=3600)
        return resultado

    # 2. Horario semanal configurado para este día
    horario = HorarioEstacionamiento.objects.filter(
        municipio=municipio, dia_semana=hoy_dia, activo=True
    ).first()

    if horario is None:
        # Sin horario configurado para hoy → libre de restricciones
        resultado = (True, None)
        cache.set(cache_key, resultado, timeout=3600)
        return resultado

    if hora_actual < horario.hora_inicio or hora_actual > horario.hora_fin:
        resultado = (False, (
            f"El estacionamiento está habilitado de "
            f"{horario.hora_inicio.strftime('%H:%M')} a "
            f"{horario.hora_fin.strftime('%H:%M')}. "
            f"Actualmente son las {hora_actual.strftime('%H:%M')}."
        ))
        cache.set(cache_key, resultado, timeout=3600)
        return resultado

    resultado = (True, None)
    cache.set(cache_key, resultado, timeout=3600)
    return resultado


def calcular_opciones_duracion(municipio, tarifa_hora, hora_inicio_est=None, duracion_actual_h=0):
    """
    Retorna lista de dicts {horas, label, costo} con múltiplos de 30 min disponibles
    hasta el cierre del día para el municipio.

    hora_inicio_est + duracion_actual_h: si se pasan (renovar), el punto de partida
    es el vencimiento actual del estacionamiento en lugar de "ahora".
    """
    ahora = timezone.localtime()
    hoy_dia = ahora.weekday()

    horario = HorarioEstacionamiento.objects.filter(
        municipio=municipio, dia_semana=hoy_dia, activo=True
    ).first()

    if horario:
        from datetime import datetime as _dt
        cierre = timezone.make_aware(
            _dt.combine(ahora.date(), horario.hora_fin),
            timezone.get_current_timezone(),
        )
        if hora_inicio_est:
            # Para renovar: calcular desde el vencimiento actual
            vencimiento_actual = hora_inicio_est + timedelta(hours=float(duracion_actual_h))
            if vencimiento_actual >= cierre:
                return []
            minutos_disponibles = int((cierre - vencimiento_actual).total_seconds() / 60)
        else:
            minutos_disponibles = int((cierre - ahora).total_seconds() / 60)
    else:
        # Sin horario configurado → máximo 8 horas
        minutos_disponibles = 8 * 60

    opciones = []
    for n in range(1, 17):          # 30 min × 1..16 → hasta 8 h
        horas = n * 0.5
        minutos = int(horas * 60)
        if minutos > minutos_disponibles:
            break
        if horas < 1:
            label = "30 min"
        elif horas == 1.0:
            label = "1 hora"
        elif horas % 1 == 0:
            label = f"{int(horas)} horas"
        else:
            label = f"{int(horas)}h 30min"
        costo = round(float(horas) * float(tarifa_hora), 2)
        opciones.append({"horas": horas, "label": label, "costo": costo})

    return opciones


def cerrar_estacionamientos_vencidos_por_horario(municipio):
    """
    Cierra todos los estacionamientos activos del municipio si el
    horario de cobro ya terminó para el día de hoy.
    Se llama en inicio_usuarios para que el cierre ocurra de forma reactiva.
    """
    from app_estacionamiento.models import HorarioEstacionamiento
    ahora       = timezone.localtime()
    hoy_dia     = ahora.weekday()
    hora_actual = ahora.time()

    horario = HorarioEstacionamiento.objects.filter(
        municipio=municipio, dia_semana=hoy_dia, activo=True
    ).first()

    # Solo cerrar si hay horario y ya pasó la hora fin
    if horario and hora_actual > horario.hora_fin:
        activos = Estacionamiento.objects.filter(
            estado="ACTIVO",
            subcuadra__municipio=municipio
        )
        for est in activos:
            finalizar_estacionamiento_uc(est)


@require_role("conductor")
def estacionar_vehiculo(request):

    usuario = request.user
    warning = None

    # 👇 para UI PRO (dropdown de vehículos)
    vehiculos = Vehiculo.objects.filter(
        vehiculousuario__usuario=usuario
    ).distinct()

    # =================================================
    # POST
    # =================================================
    if request.method == "POST":

        # =============================================
        # 1. INPUTS (compatibilidad vieja + nueva UI)
        # =============================================

        patente = (request.POST.get("patente") or "").strip().upper()
        vehiculo_id = request.POST.get("vehiculo_id")

        duracion = request.POST.get("duracion") or request.POST.get("horas")

        # =============================================
        # 2. VEHÍCULO
        # =============================================

        if vehiculo_id:
            # Verificar que el vehículo pertenece a este conductor
            # (evita manipulación del vehiculo_id por POST manual)
            vehiculo = get_object_or_404(
                Vehiculo,
                id=vehiculo_id,
                vehiculousuario__usuario=usuario
            )
        else:
            if not patente:
                return render(request, "usuarios/estacionar_vehiculo.html", {
                    "error": "Debe ingresar una patente",
                    "vehiculos": vehiculos,
                    "usuario": usuario
                })

            vehiculo, _ = Vehiculo.objects.get_or_create(
                patente=patente
            )

        # municipio
        if not vehiculo.municipio:
            vehiculo.municipio = usuario.municipio
            vehiculo.save()

        # =============================================
        # 3. RELACIÓN
        # =============================================

        relacion, _ = VehiculoUsuario.objects.get_or_create(
            usuario=usuario,
            vehiculo=vehiculo,
            defaults={
                "es_propietario": True,
                "verificado": False
            }
        )

        # =============================================
        # 5. VALIDACIONES
        # =============================================

        if vehiculo.exento_global:
            return render(request, "inspectores/verificar_vehiculo.html", {
                "resultado": {
                    "patente": vehiculo.patente,
                    "estado": "Exento TOTAL",
                    "estacionamiento_activo": True
                }
            })

        if Estacionamiento.objects.filter(
            vehiculo=vehiculo,
            estado="ACTIVO"
        ).exists():
            return render(request, "usuarios/estacionar_vehiculo.html", {
                "error": "El vehículo ya tiene un estacionamiento activo.",
                "warning": warning,
                "vehiculos": vehiculos,
                "usuario": usuario
            })

        # =============================================
        # 6. VALIDACIÓN DE HORARIO
        # =============================================

        permitido, msg_horario = puede_estacionar_ahora(usuario.municipio)
        if not permitido:
            return render(request, "usuarios/estacionar_vehiculo.html", {
                "error": msg_horario,
                "warning": warning,
                "vehiculos": vehiculos,
                "usuario": usuario,
            })

        # =============================================
        # 7. DURACIÓN
        # =============================================

        try:
            duracion = Decimal(duracion)
            if duracion <= 0:
                raise ValueError()
        except:
            return render(request, "usuarios/estacionar_vehiculo.html", {
                "error": "Duración inválida",
                "warning": warning,
                "vehiculos": vehiculos,
                "usuario": usuario
            })

        # =============================================
        # 7. COSTO
        # =============================================
        subcuadra = get_subcuadra_default(usuario.municipio)

        result = ejecutar_estacionamiento(
            usuario,
            vehiculo,
            subcuadra,
            duracion
        )

        # Mostrar warnings al usuario antes de redirigir
        for w in result.get("warnings", []):
            messages.warning(request, w)

        if not result["ok"]:
            return redirect(reverse(result["redirect"]))

        # Verificar si el inspector escaneó este vehículo recientemente
        # (dentro del plazo de tolerancia). Si pagó a tiempo → avisar.
        from datetime import timedelta
        tolerancia = timedelta(minutes=15)
        escaneado_recientemente = VerificacionInspector.objects.filter(
            vehiculo=vehiculo,
            fecha__gte=timezone.now() - tolerancia
        ).exists()
        if escaneado_recientemente:
            messages.info(
                request,
                "⚠️ Tu vehículo fue escaneado por un inspector. "
                "Como pagaste a tiempo, la infracción quedó cancelada."
            )

        return redirect(reverse(result["redirect"]))

    # =================================================
    # GET
    # =================================================

    from app_estacionamiento.models import Tarifa
    tarifa_obj = Tarifa.objects.filter(municipio=usuario.municipio).first()
    tarifa_hora_auto = tarifa_obj.precio_por_hora if tarifa_obj else 100
    tarifa_hora_moto = (
        tarifa_obj.precio_por_hora_moto
        if tarifa_obj and tarifa_obj.precio_por_hora_moto
        else tarifa_hora_auto
    )

    # Patente preseleccionada (viene del flujo agregar_vehiculo)
    patente_preseleccionada = request.GET.get("patente", "").strip().upper()

    # Opciones de duración calculadas con tarifa de auto (se ajusta con JS en el template)
    opciones_duracion = calcular_opciones_duracion(usuario.municipio, tarifa_hora_auto)

    return render(request, "usuarios/estacionar_vehiculo.html", {
        "vehiculos": vehiculos,
        "usuario": usuario,
        "tarifa_hora": tarifa_hora_auto,
        "tarifa_hora_auto": tarifa_hora_auto,
        "tarifa_hora_moto": tarifa_hora_moto,
        "patente_preseleccionada": patente_preseleccionada,
        "opciones_duracion": opciones_duracion,
    })

@require_role("conductor")
def historial_estacionamientos(request):
    usuario = request.user

    estacionamientos = (
        Estacionamiento.objects
        .filter(usuario=usuario)
        .order_by("-hora_inicio")
    )

    return render(
        request,
        "usuarios/historial_estacionamientos.html",
        {
            "estacionamientos": estacionamientos
        }
    )

@require_role("conductor")
def renovar_estacionamiento(request, est_id):
    """
    Permite al conductor extender las horas de su estacionamiento activo.
    Cobra la diferencia de saldo según la tarifa vigente.
    """
    from app_estacionamiento.models import Tarifa

    usuario = request.user
    estacionamiento = get_object_or_404(
        Estacionamiento,
        id=est_id,
        usuario=usuario,
        estado="ACTIVO",
    )

    tarifa_obj = Tarifa.objects.filter(municipio=usuario.municipio).first()
    tarifa_hora = tarifa_obj.precio_por_hora if tarifa_obj else Decimal("100")

    error = None

    if request.method == "POST":
        try:
            horas_extra = Decimal(request.POST.get("horas_extra", "0"))
            if horas_extra <= 0:
                raise ValueError()
        except Exception:
            error = "Ingresá una cantidad de horas válida."
        else:
            costo_extra = horas_extra * tarifa_hora

            if usuario.saldo < costo_extra:
                error = f"Saldo insuficiente. Necesitás ${costo_extra:.2f} y tenés ${usuario.saldo:.2f}."
            else:
                with transaction.atomic():
                    usuario_db = Usuario.objects.select_for_update().get(id=usuario.id)
                    if usuario_db.saldo < costo_extra:
                        error = "Saldo insuficiente."
                    else:
                        # Extender duración y cobrar
                        estacionamiento.duracion_horas = estacionamiento.duracion_horas + int(horas_extra)
                        estacionamiento.save(update_fields=["duracion_horas"])

                        usuario_db.saldo -= costo_extra
                        usuario_db.save(update_fields=["saldo"])

                        MovimientoCaja.objects.create(
                            usuario=usuario_db,
                            monto=costo_extra,
                            tipo="egreso",
                            descripcion=f"Renovación {horas_extra:.0f}h — {estacionamiento.vehiculo.patente}",
                        )

                        messages.success(
                            request,
                            f"✅ Estacionamiento extendido {horas_extra:.0f}h más. "
                            f"Se descontaron ${costo_extra:.2f} de tu saldo."
                        )
                        return redirect("inicio_usuarios")

    # Opciones de horas extra limitadas al horario de cierre del municipio
    opciones_duracion = calcular_opciones_duracion(
        municipio=usuario.municipio,
        tarifa_hora=tarifa_hora,
        hora_inicio_est=estacionamiento.hora_inicio,
        duracion_actual_h=float(estacionamiento.duracion_horas),
    )

    return render(request, "usuarios/renovar_estacionamiento.html", {
        "estacionamiento": estacionamiento,
        "tarifa_hora": tarifa_hora,
        "saldo": usuario.saldo,
        "error": error,
        "opciones_duracion": opciones_duracion,
    })


@require_role("conductor")
def finalizar_estacionamiento(request, estacionamiento_id):

    estacionamiento = get_object_or_404(
        Estacionamiento,
        id=estacionamiento_id,
        usuario=request.user
    )

    if estacionamiento.estado != Estado.ACTIVO:
        return redirect("usuarios_historial_estacionamientos")

    # GET → mostrar pantalla de confirmación con el costo estimado
    if request.method != "POST":
        duracion_horas = estacionamiento.duracion_horas
        return render(request, "usuarios/finalizar_estacionamiento.html", {
            "estacionamiento": estacionamiento,
            "duracion_horas": duracion_horas,
            "costo_estimado": estacionamiento.costo_base,
            "usuario": request.user,
        })

    # POST → ejecutar y mostrar resultado
    resultado = finalizar_estacionamiento_uc(estacionamiento)

    if resultado["ok"]:
        messages.success(
            request,
            f"Estacionamiento finalizado. Costo: ${resultado['costo']}"
        )
    else:
        messages.error(request, resultado.get("error", "Error al finalizar"))

    return redirect("usuarios_historial_estacionamientos")

@require_login
def mis_infracciones(request):
    usuario = request.user

    # Solo conductores tienen infracciones propias.
    # Inspectores / admins / vendedores → redirigir a su panel.
    if not usuario.es_conductor:
        messages.info(request, "Esta sección es solo para conductores.")
        return redirect_por_rol(usuario)

    # Conductores no verificados: solo ven las infracciones de sus vehículos.
    # Conductores verificados: ídem (en el futuro podríamos cruzar con el RNPA).
    if not usuario.es_verificado and not usuario.vehiculos.exists():
        messages.info(
            request,
            "No tenés vehículos registrados. "
            "Agregá tu vehículo o verificá tu cuenta para ver tus infracciones."
        )
        return redirect("solicitar_verificacion")

    infracciones = (
        Infraccion.objects
        .filter(vehiculo__vehiculousuario__usuario=usuario)
        .distinct()
        .order_by("-creado_en")
    )

    return render(
        request,
        "usuarios/historial_infracciones.html",
        {
            "infracciones": infracciones,
            "saldo_usuario": usuario.saldo,
            "tiene_pendientes": infracciones.filter(estado="pendiente").exists(),
        }
    )

@require_login
@require_role("admin", "vendedor", "inspector")
def consultar_deuda(request):
    """
    Admin/vendedor/inspector: busca infracciones pendientes por patente y las cobra.
    Flujo:
      GET                  -> formulario de búsqueda
      POST accion=confirmar -> mostrar modal de confirmación en el template
      POST accion=cobrar    -> cobrar (con tolerancia de gracia), redirect al comprobante
    """
    municipio = request.user.municipio
    patente = (request.GET.get("patente") or "").strip().upper()
    infracciones = []
    vehiculo = None
    infraccion_a_confirmar = None

    if patente:
        from django.db.models import Q as _Q
        vehiculo = Vehiculo.objects.filter(patente=patente).filter(
            _Q(municipio=municipio) | _Q(municipio__isnull=True)
        ).first()
        if vehiculo:
            infracciones = Infraccion.objects.filter(
                vehiculo=vehiculo,
                municipio=municipio,
                estado="pendiente",
            ).order_by("-creado_en")

    if request.method == "POST":
        accion = request.POST.get("accion")
        infraccion_id = request.POST.get("infraccion_id")

        # Paso 1: solicitar confirmación
        if accion == "confirmar" and infraccion_id:
            patente = (request.POST.get("patente") or "").strip().upper()
            infraccion_a_confirmar = Infraccion.objects.filter(
                id=infraccion_id, municipio=municipio, estado="pendiente"
            ).select_related("vehiculo", "inspector").first()
            if not infraccion_a_confirmar:
                messages.error(request, "Infracción no encontrada o ya procesada.")
                return redirect(f"{request.path}?patente={patente}")
            from django.db.models import Q as _Q3
            if not vehiculo:
                vehiculo = Vehiculo.objects.filter(patente=patente).filter(
                    _Q3(municipio=municipio) | _Q3(municipio__isnull=True)
                ).first()
            if vehiculo:
                infracciones = Infraccion.objects.filter(
                    vehiculo=vehiculo, municipio=municipio, estado="pendiente"
                ).order_by("-creado_en")
            return render(request, "usuarios/consultar_deuda.html", {
                "patente": patente,
                "vehiculo": vehiculo,
                "infracciones": infracciones,
                "infraccion_a_confirmar": infraccion_a_confirmar,
            })

        # Paso 2: ejecutar cobro
        elif accion == "cobrar" and infraccion_id:
            try:
                with transaction.atomic():
                    inf = get_object_or_404(
                        Infraccion.objects.select_for_update(),
                        id=infraccion_id,
                        municipio=municipio,
                        estado="pendiente",
                    )
                    # Tolerancia de gracia
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
                        comision = round(inf.monto * comision_pct / 100, 2)
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
        "patente": patente,
        "vehiculo": vehiculo,
        "infracciones": infracciones,
        "infraccion_a_confirmar": None,
    })

@require_role("admin", "vendedor", "inspector")
def ticket_pago_multa(request, infraccion_id):
    """
    Comprobante de pago (o anulación por gracia) de una infracción.
    Imprime automáticamente y redirige al panel del usuario.
    """
    infraccion = get_object_or_404(
        Infraccion,
        id=infraccion_id,
        municipio=request.user.municipio,
    )
    # Solo mostrar si fue procesada (pagada o anulada)
    if infraccion.estado not in ("pagada", "anulada"):
        messages.warning(request, "Esta infracción aún está pendiente.")
        return redirect("consultar_deuda")

    return render(request, "ticket_pago_multa.html", {
        "infraccion": infraccion,
        "cobrado_por": request.user,
    })


# =========================================================
# VIEWS INSPECTORES
# =========================================================
@require_role("inspector")
def panel_inspectores(request):
    inspector = request.user

    # Movimientos no cerrados (lo que debe rendir)
    movimientos_abiertos = MovimientoCaja.objects.filter(
        usuario=inspector, tipo="ingreso", cerrado=False
    )
    a_rendir = movimientos_abiertos.aggregate(total=Sum("monto"))["total"] or 0

    # Saldo operativo total acumulado
    total_ingresos = MovimientoCaja.objects.filter(
        usuario=inspector, tipo="ingreso"
    ).aggregate(total=Sum("monto"))["total"] or 0
    total_egresos = MovimientoCaja.objects.filter(
        usuario=inspector, tipo="egreso"
    ).aggregate(total=Sum("monto"))["total"] or 0
    saldo_operativo = total_ingresos - total_egresos

    # Infracciones y no pagados del municipio
    total_infracciones = Infraccion.objects.filter(
        municipio=inspector.municipio, inspector=inspector
    ).count()
    no_pagados = Infraccion.objects.filter(
        municipio=inspector.municipio, inspector=inspector, estado="pendiente"
    ).count()

    resumen = {
        "saldo_operativo": saldo_operativo,
        "a_rendir": a_rendir,
        "infracciones": total_infracciones,
        "no_pagados": no_pagados,
    }

    return render(request, "inspectores/panel_inspectores.html", {"resumen": resumen})

@require_role("inspector", "admin")
def gestion_infracciones(request):

    usuario = request.user

    infracciones = Infraccion.objects.filter(
        municipio=usuario.municipio
    ).select_related("vehiculo", "inspector").order_by("-creado_en")

    return render(request, "usuarios/historial_infracciones.html", {
        "usuario": usuario,
        "infracciones": infracciones,
        # Pasar valores seguros para que el template no falle en comparaciones
        "saldo_usuario": 0,
        "tiene_pendientes": False,
        "es_vista_gestion": True,  # el template puede ocultarlos botones de pago
    })

@require_role("inspector")
def verificar_vehiculo(request):
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
                # Vehiculo no registrado: crearlo con el tipo indicado
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

@require_role("inspector")
def registrar_infraccion(request):
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
        messages.error(
            request,
            "No existe subcuadra configurada."
        )
        return redirect("panel_inspectores")

    ultima_infraccion = Infraccion.objects.filter(inspector=usuario).order_by("-creado_en").first()
    subcuadra_default = (ultima_infraccion.subcuadra_id if ultima_infraccion else None)
    infracciones_recientes = Infraccion.objects.filter( vehiculo=vehiculo).order_by("-id")[:3]

    # 🚀 NUEVO: validación previa (clave para UX real)
    resultado = verificar_estado_vehiculo(patente, request.user, subcuadra)

    # ==============================
    # POST → usar service
    # ==============================
    if request.method == "POST":
        try:
            # Coordenadas GPS enviadas desde el frontend (JS)
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

    # Todas las subcuadras del municipio para que el inspector pueda elegir
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
    infraccion = get_object_or_404(Infraccion, id=infraccion_id, municipio=request.user.municipio)

    return render(request, "ticket_infraccion.html", {
        "infraccion": infraccion,
    })

@require_role("inspector", "vendedor", "admin")
def caja_inspector(request):
    """
    Vista de caja compartida para inspectores y vendedores.
    Muestra movimientos del período actual, permite cerrar caja,
    y muestra el historial de cierres anteriores con su estado de certificación.
    """
    usuario = request.user
    municipio = getattr(usuario, "municipio", None)
    if not municipio:
        return redirect("login")

    movimientos = MovimientoCaja.objects.filter(
        usuario=usuario
    ).order_by("-creado_en")

    total_ingresos = movimientos.filter(tipo="ingreso").aggregate(
        total=Sum("monto"))["total"] or 0
    total_egresos = movimientos.filter(tipo="egreso").aggregate(
        total=Sum("monto"))["total"] or 0

    movimientos_pendientes = movimientos.filter(tipo="ingreso", cerrado=False)
    total_a_cerrar = movimientos_pendientes.aggregate(
        total=Sum("monto"))["total"] or 0

    # Historial de cierres anteriores de este usuario
    historial_cierres = CierreCaja.objects.filter(
        usuario=usuario
    ).select_related("certificado_por").order_by("-fecha_cierre")[:20]

    return render(request, "inspectores/caja.html", {
        "movimientos": movimientos,
        "ingresos": total_ingresos,
        "egresos": total_egresos,
        "saldo": total_ingresos - total_egresos,
        "movimientos_abiertos": movimientos_pendientes.count(),
        "total_a_cerrar": total_a_cerrar,
        "historial_cierres": historial_cierres,
    })

# =========================================================
# VIEWS COMPARTIDAS INSPECTORES + VENDEDORES
# =========================================================
@require_role("vendedor", "admin")
def registrar_estacionamiento_manual(request):
    inspector = request.user
    from app_estacionamiento.models import Tarifa

    tarifa_obj = Tarifa.objects.filter(municipio=inspector.municipio).first()
    tarifa_hora = tarifa_obj.precio_por_hora if tarifa_obj else Decimal("100")
    opciones_duracion = calcular_opciones_duracion(inspector.municipio, tarifa_hora)

    def _render_form(error=None):
        return render(request, "inspectores/registrar_estacionamiento_manual.html", {
            "error": error,
            "tarifa_hora": tarifa_hora,
            "opciones_duracion": opciones_duracion,
        })

    if request.method != "POST":
        return _render_form()

    patente = (request.POST.get("patente") or "").strip().upper()
    duracion_raw = request.POST.get("duracion")

    if not patente:
        return _render_form("Ingresa la patente del vehiculo.")

    # Validar horario del municipio
    permitido, msg_horario = puede_estacionar_ahora(inspector.municipio)
    if not permitido:
        return _render_form(msg_horario)

    # Validar duracion contra el horario de cierre
    try:
        duracion = Decimal(str(duracion_raw))
        if duracion <= 0 or (duracion * 2) % 1 != 0:
            raise ValueError()
    except Exception:
        return _render_form("Duracion invalida. Selecciona una opcion de la lista.")

    # Verificar que la duracion elegida este dentro de las opciones validas
    valores_validos = [op["horas"] for op in opciones_duracion]
    if float(duracion) not in valores_validos:
        return _render_form(
            "La duracion seleccionada excede el horario de cierre del estacionamiento."
        )

    vehiculo, _ = Vehiculo.objects.get_or_create(
        patente=patente,
        defaults={"municipio": inspector.municipio}
    )
    if not vehiculo.municipio:
        vehiculo.municipio = inspector.municipio
        vehiculo.save()

    # Bloquear cobro manual a vehiculos exentos
    if getattr(vehiculo, "exento_global", False):
        return _render_form(f"El vehiculo {patente} tiene exencion total — no se puede cobrar.")

    if Estacionamiento.objects.filter(vehiculo=vehiculo, estado="ACTIVO").exists():
        return _render_form("El vehiculo ya tiene un estacionamiento activo.")

    subcuadra = get_subcuadra_default(inspector.municipio)
    if not subcuadra:
        return _render_form("No hay subcuadra configurada para este municipio.")

    monto = duracion * tarifa_hora

    with transaction.atomic():
        # 1. Crear el estacionamiento
        est = EstacionamientoFactory.crear(
            usuario=inspector,
            vehiculo=vehiculo,
            subcuadra=subcuadra,
            duracion=duracion,
            costo_base=monto,
        )
        # 2. Registrar el ingreso en caja del inspector
        cobrar_estacionamiento(
            inspector=inspector,
            monto=monto,
            descripcion=f"Cobro manual {vehiculo.patente}",
        )

    return redirect(reverse("inspectores_ticket_cobro", args=[est.id]))

@require_role("vendedor", "admin")
def registrar_estacionamiento_vendedor(request):
    """
    El vendedor cobra en efectivo: registra el estacionamiento en el sistema
    y crea un INGRESO en su caja. No descuenta saldo propio.
    Respeta el horario del municipio (igual que el conductor).
    """
    vendedor = request.user
    from app_estacionamiento.models import Tarifa

    tarifa_obj = Tarifa.objects.filter(municipio=vendedor.municipio).first()
    tarifa_hora_auto = tarifa_obj.precio_por_hora if tarifa_obj else Decimal("100")
    tarifa_hora_moto = (
        tarifa_obj.precio_por_hora_moto
        if tarifa_obj and tarifa_obj.precio_por_hora_moto
        else tarifa_hora_auto
    )
    tarifa_hora = tarifa_hora_auto
    opciones_duracion = calcular_opciones_duracion(vendedor.municipio, tarifa_hora)

    def _render_form(error=None):
        return render(request, "vendedores/registrar_estacionamiento.html", {
            "error": error,
            "tarifa_hora": tarifa_hora,
            "tarifa_hora_auto": tarifa_hora_auto,
            "tarifa_hora_moto": tarifa_hora_moto,
            "opciones_duracion": opciones_duracion,
        })

    if request.method != "POST":
        return _render_form()

    patente = (request.POST.get("patente") or "").strip().upper()
    duracion_raw = request.POST.get("duracion")

    if not patente:
        return _render_form("Ingresá la patente del vehículo.")

    # Validar horario del municipio
    permitido, msg_horario = puede_estacionar_ahora(vendedor.municipio)
    if not permitido:
        return _render_form(msg_horario)

    # Validar duración (múltiplos de 0.5 h)
    try:
        duracion = Decimal(str(duracion_raw))
        if duracion <= 0 or (duracion * 2) % 1 != 0:
            raise ValueError()
    except Exception:
        return _render_form("Duración inválida.")

    vehiculo, _ = Vehiculo.objects.get_or_create(
        patente=patente,
        defaults={"municipio": vendedor.municipio}
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

    # Usar tarifa según tipo de vehículo
    es_moto = getattr(vehiculo, "tipo", "auto") == "moto"
    tarifa_cobro = tarifa_hora_moto if es_moto else tarifa_hora_auto
    monto = duracion * tarifa_cobro

    # Comision del vendedor sobre este cobro
    comision_pct = getattr(vendedor.municipio, "comision_vendedor", None) or Decimal("0")
    comision_cobro = (monto * comision_pct / 100).quantize(Decimal("0.01"))

    with transaction.atomic():
        est = EstacionamientoFactory.crear(
            usuario=vendedor,
            vehiculo=vehiculo,
            subcuadra=subcuadra,
            duracion=duracion,
            costo_base=monto,
        )
        # Registrar el efectivo cobrado en la caja del vendedor con su comision
        cobrar_estacionamiento(
            inspector=vendedor,
            monto=monto,
            descripcion=f"Estacionamiento {patente}",
            comision_monto=comision_cobro,
        )

    return redirect(reverse("inspectores_ticket_cobro", args=[est.id]))

@require_role("inspector", "vendedor", "admin")
def resumen_cobros(request):
    usuario = request.user

    # Filtrar por municipio del usuario autenticado
    cobros = MovimientoCaja.objects.filter(
        usuario__municipio=usuario.municipio
    ).select_related("usuario").order_by("-creado_en")

    return render(request, 'inspectores/resumen_cobros.html', {
        "cobros": cobros
    })

@require_role("vendedor", "inspector", "admin")
def ticket_cobro(request, est_id):
    # Verifica municipio para que un usuario de otro municipio no acceda
    est = get_object_or_404(
        Estacionamiento,
        id=est_id,
        subcuadra__municipio=request.user.municipio
    )

    return render(request, "ticket.html", {
        "patente": est.vehiculo.patente,
        "duracion": est.duracion_horas,
        "hora": est.hora_inicio,
        "monto": est.costo_base
    })

@require_role("inspector", "admin")
def resumen_infracciones(request):
    usuario = request.user

    infracciones = Infraccion.objects.filter(
        municipio=usuario.municipio
    ).select_related("vehiculo", "subcuadra", "inspector").order_by("-creado_en")

    return render(request, "inspectores/resumen_infracciones.html", {
        "infracciones": infracciones
    })

# =========================================================


# =========================================================
# ABONO MENSUAL — vendedor cobra abono a conductor
# =========================================================
@require_role("vendedor", "admin")
def cobrar_abono(request):
    """
    El vendedor cobra el abono mensual de un vehiculo.

    Flujo:
    - GET/POST sin confirmar: muestra formulario de patente
    - POST accion=confirmar: muestra resumen antes de cobrar
    - POST accion=cobrar: registra el AbonoMensual y el MovimientoCaja
    """
    from datetime import date
    vendedor  = request.user
    municipio = vendedor.municipio

    tarifa_obj = Tarifa.objects.filter(municipio=municipio).first()

    error     = None
    vehiculo  = None
    confirmar = False
    precio    = None

    if request.method == "POST":
        accion  = request.POST.get("accion", "buscar")
        patente = (request.POST.get("patente") or "").strip().upper()

        if not patente:
            error = "Ingresa la patente del vehiculo."
        else:
            vehiculo = Vehiculo.objects.filter(patente=patente).first()
            if not vehiculo:
                error = f"No existe ningun vehiculo con patente {patente}."
            else:
                # Calcular precio segun tipo
                es_moto    = getattr(vehiculo, "tipo", "auto") == "moto"
                precio_moto = getattr(tarifa_obj, "precio_abono_moto", None) if tarifa_obj else None
                precio_auto = getattr(tarifa_obj, "precio_abono_auto", None) if tarifa_obj else None

                if es_moto and precio_moto and precio_moto > 0:
                    precio = precio_moto
                elif precio_auto and precio_auto > 0:
                    precio = precio_auto
                else:
                    error = "No hay tarifa de abono configurada. Configurala en Tarifas."

                if not error:
                    hoy        = date.today()
                    mes_actual = hoy.replace(day=1)

                    # Verificar si ya tiene abono este mes
                    ya_tiene = AbonoMensual.objects.filter(
                        vehiculo=vehiculo,
                        municipio=municipio,
                        mes=mes_actual,
                    ).exists()

                    if ya_tiene:
                        error = f"El vehiculo {patente} ya tiene abono activo para este mes."
                    elif accion == "confirmar":
                        confirmar = True
                    elif accion == "cobrar":
                        # Calcular comision
                        comision_pct = getattr(municipio, 'comision_vendedor', None) or Decimal('0')
                        comision_monto = (precio * comision_pct / 100).quantize(Decimal("0.01"))

                        with transaction.atomic():
                            movimiento = MovimientoCaja.objects.create(
                                usuario=vendedor,
                                monto=precio,
                                tipo="ingreso",
                                descripcion="Abono mensual " + mes_actual.strftime("%m/%Y") + " - " + patente,
                                medio_pago="efectivo",
                                comision_monto=comision_monto,
                            )
                            AbonoMensual.objects.create(
                                vehiculo=vehiculo,
                                municipio=municipio,
                                vendedor=vendedor,
                                mes=mes_actual,
                                monto=precio,
                                medio_pago="efectivo",
                                movimiento_caja=movimiento,
                            )

                        messages.success(
                            request,
                            f"Abono registrado para {patente} — ${precio}. "
                            f"Comision generada: ${comision_monto}."
                        )
                        return redirect("cobrar_abono")

    return render(request, "vendedores/cobrar_abono.html", {
        "vehiculo":  vehiculo,
        "precio":    precio,
        "confirmar": confirmar,
        "error":     error,
        "tarifa_obj": tarifa_obj,
    })

# VIEWS VENDEDORES
# =========================================================
@require_role("vendedor")
def panel_vendedor(request):
    from django.utils import timezone as tz

    user = request.user
    hoy = tz.localdate()

    # Movimientos del día actual
    movimientos_hoy = MovimientoCaja.objects.filter(
        usuario=user,
        tipo="ingreso",
        creado_en__date=hoy,
    )
    total_hoy = movimientos_hoy.aggregate(total=Sum("monto"))["total"] or 0
    cantidad_operaciones = movimientos_hoy.count()

    # Movimientos pendientes de cierre (a rendir)
    a_rendir = MovimientoCaja.objects.filter(
        usuario=user, tipo="ingreso", cerrado=False
    ).aggregate(total=Sum("monto"))["total"] or 0

    # Comisiones acumuladas del vendedor (total histórico)
    # Las liquidaciones certificadas ya fueron cobradas, pero
    # mostramos el total completo como referencia de saldo a favor.
    comisiones_pendientes = MovimientoCaja.objects.filter(
        usuario=user,
        tipo="ingreso",
        comision_monto__gt=0,
    ).aggregate(total=Sum("comision_monto"))["total"] or 0

    return render(request, "vendedores/panel.html", {
        "total_hoy": total_hoy,
        "cantidad_operaciones": cantidad_operaciones,
        "a_rendir": a_rendir,
        "comisiones_pendientes": comisiones_pendientes,
    })

@require_role("vendedor", "admin")
def resumen_caja(request):
    """Resumen de movimientos de caja del vendedor/inspector."""
    usuario = request.user
    hoy = timezone.localdate()

    # Movimientos de hoy
    cobros_hoy = MovimientoCaja.objects.filter(
        usuario=usuario,
        tipo="ingreso",
        creado_en__date=hoy,
    ).order_by("-creado_en")

    # Movimientos pendientes de cierre
    cobros_abiertos = MovimientoCaja.objects.filter(
        usuario=usuario,
        tipo="ingreso",
        cerrado=False,
    ).order_by("-creado_en")

    total_hoy = cobros_hoy.aggregate(total=Sum("monto"))["total"] or 0
    total_abierto = cobros_abiertos.aggregate(total=Sum("monto"))["total"] or 0

    return render(request, "vendedores/resumen_caja.html", {
        "cobros_hoy": cobros_hoy,
        "cobros_abiertos": cobros_abiertos,
        "total_hoy": total_hoy,
        "total_abierto": total_abierto,
    })


@require_role("vendedor", "admin")
def cobrar_infraccion_vendedor(request):
    """
    El kiosco/vendedor ingresa una patente, ve la infracción pendiente
    y la cobra en efectivo. El monto queda registrado en su caja.

    Nota: no valida horario de estacionamiento — el kiosco siempre puede cobrar.
    """
    vendedor = request.user
    municipio = vendedor.municipio
    infraccion = None
    vehiculo = None
    patente = ""

    if request.method == "POST":
        accion = request.POST.get("accion")
        patente = (request.POST.get("patente") or "").strip().upper()

        if accion == "buscar" and patente:
            # Buscar vehículo en el municipio (o sin municipio asignado)
            vehiculo = Vehiculo.objects.filter(
                patente=patente
            ).filter(
                Q(municipio=municipio) | Q(municipio__isnull=True)
            ).first()

            if vehiculo:
                infraccion = Infraccion.objects.filter(
                    vehiculo=vehiculo,
                    municipio=municipio,
                    estado="pendiente"
                ).order_by("-creado_en").first()

                if not infraccion:
                    messages.info(request, f"El vehículo {patente} no tiene infracciones pendientes.")
            else:
                messages.warning(request, f"No se encontró el vehículo con patente {patente}.")

        elif accion == "confirmar":
            # Paso 1: mostrar modal de confirmación con todos los datos
            infraccion_id = request.POST.get("infraccion_id")
            patente_post = (request.POST.get("patente") or "").strip().upper()
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
                "vehiculo": vehiculo,
                "patente": patente_post,
                "confirmar": True,
            })

        elif accion == "cobrar":
            infraccion_id = request.POST.get("infraccion_id")
            if infraccion_id:
                try:
                    with transaction.atomic():
                        inf = get_object_or_404(
                            Infraccion.objects.select_for_update(),
                            id=infraccion_id,
                            municipio=municipio,
                            estado="pendiente",
                        )
                        # Tolerancia de gracia
                        from datetime import timedelta as _td3
                        tolerancia_min = municipio.tolerancia_multa_minutos or 0
                        ahora = timezone.now()
                        anulada_por_gracia = (
                            tolerancia_min > 0 and
                            (ahora - inf.creado_en) <= _td3(minutes=tolerancia_min)
                        )
                        if anulada_por_gracia:
                            inf.estado = "anulada"
                        else:
                            inf.estado = "pagada"
                            comision_pct = municipio.comision_vendedor or 0
                            comision = round(inf.monto * comision_pct / 100, 2)
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
        "vehiculo": vehiculo,
        "patente": patente,
    })


@require_role("inspector", "vendedor", "admin")
def cerrar_caja(request):
    usuario = request.user

    # GET → mostrar resumen de lo que se va a cerrar
    if request.method != "POST":
        from django.db.models import Sum
        movimientos_abiertos = MovimientoCaja.objects.filter(
            usuario=usuario,
            tipo="ingreso",
            cerrado=False
        ).order_by("creado_en")

        total_a_cerrar = movimientos_abiertos.aggregate(
            total=Sum("monto")
        )["total"] or 0

        return render(request, "inspectores/caja.html", {
            "movimientos": MovimientoCaja.objects.filter(usuario=usuario).order_by("-creado_en"),
            "movimientos_abiertos": movimientos_abiertos.count(),
            "total_a_cerrar": total_a_cerrar,
            "ingresos": MovimientoCaja.objects.filter(usuario=usuario, tipo="ingreso").aggregate(total=Sum("monto"))["total"] or 0,
            "egresos": MovimientoCaja.objects.filter(usuario=usuario, tipo="egreso").aggregate(total=Sum("monto"))["total"] or 0,
            "saldo": (MovimientoCaja.objects.filter(usuario=usuario, tipo="ingreso").aggregate(total=Sum("monto"))["total"] or 0)
                   - (MovimientoCaja.objects.filter(usuario=usuario, tipo="egreso").aggregate(total=Sum("monto"))["total"] or 0),
        })

    # POST → ejecutar cierre
    cierre = generar_cierre_caja(usuario)

    if cierre:
        messages.success(request, f"Caja cerrada. Total: ${cierre.total_cobrado}")
    else:
        messages.warning(request, "No había movimientos abiertos para cerrar.")

    # Redirigir al panel que corresponde según el rol
    usuario = request.user
    if getattr(usuario, "es_vendedor", False):
        return redirect("panel_vendedor")
    elif getattr(usuario, "es_inspector", False):
        return redirect("panel_inspectores")
    else:
        return redirect("inicio_admin")

@require_login
def simular_pago(request, infraccion_id):
    # Solo disponible en modo desarrollo (DEBUG=True).
    # En producción devuelve 404 para evitar que se bypass el pago real.
    if not settings.DEBUG:
        from django.http import Http404
        raise Http404("No disponible en producción.")

    infraccion = get_object_or_404(Infraccion, id=infraccion_id)
    infraccion.estado = "pagada"
    infraccion.save()
    return redirect("inspectores_ticket", infraccion.id)

# =========================================================
# VIEWS GESTIÓN ADMIN
# =========================================================

@require_role("admin")
def inicio_admin(request):
    usuario = request.user
    municipio = usuario.municipio

    return render(request, "admin/inicio_admin.html", {
        "total_usuarios": Usuario.objects.filter(es_conductor=True, municipio=municipio).count(),
        "total_inspectores": Usuario.objects.filter(es_inspector=True, municipio=municipio).count(),
        "total_vendedores": Usuario.objects.filter(es_vendedor=True, municipio=municipio).count(),
        "activos": Estacionamiento.objects.filter(estado=Estado.ACTIVO, subcuadra__municipio=municipio).count(),
        "eventos_recientes": [],  # TODO: implementar log de auditoría
    })

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

    # Editar datos básicos del conductor
    elif accion == "editar_datos":
        nombre   = request.POST.get("nombre", "").strip()
        apellido = request.POST.get("apellido", "").strip()
        if nombre or apellido:
            if nombre:
                conductor.first_name = nombre
            if apellido:
                conductor.last_name = apellido
            conductor.save(update_fields=["first_name", "last_name"])
            messages.success(request, "Datos actualizados.")

    # Historial de infracciones de sus vehículos
    infracciones = Infraccion.objects.filter(
        vehiculo__vehiculousuario__usuario=conductor,
        municipio=request.user.municipio,
    ).distinct().order_by("-creado_en")[:20]

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
# VIEWS LOGIN / LOGOUT
# =========================================================
def logout_view(request):
    # Solo POST para prevenir logout por CSRF (links maliciosos como <img src="/logout/">)
    if request.method == "POST":
        logout(request)
    return redirect("login")


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

@require_role("tesorero")
def panel_tesorero(request):
    """Panel principal del tesorero: ve rendiciones y liquidaciones pendientes."""
    municipio = request.user.municipio

    rendiciones = Rendicion.objects.filter(
        municipio=municipio
    ).select_related("admin").order_by("-creado_en")[:50]

    liquidaciones = LiquidacionComision.objects.filter(
        municipio=municipio
    ).select_related("vendedor").order_by("-creado_en")[:50]

    pendientes_rendicion   = rendiciones.filter(estado="pendiente").count()
    pendientes_liquidacion = liquidaciones.filter(estado="pendiente").count()

    return render(request, "tesorero/panel_tesorero.html", {
        "rendiciones": rendiciones,
        "liquidaciones": liquidaciones,
        "pendientes_rendicion": pendientes_rendicion,
        "pendientes_liquidacion": pendientes_liquidacion,
    })




@require_role("tesorero")
def depositar_comision(request, liquidacion_id):
    """
    Tesoreria marca una liquidacion como depositada
    y registra quien la depositio y cuando.
    """
    municipio    = request.user.municipio
    liquidacion  = get_object_or_404(LiquidacionComision, id=liquidacion_id, municipio=municipio)

    if liquidacion.estado != "pendiente":
        messages.warning(request, "Esta liquidacion ya fue procesada.")
        return redirect("panel_tesorero")

    if request.method == "POST":
        notas = request.POST.get("notas_tesorero", "").strip()
        with transaction.atomic():
            liquidacion.estado       = "depositada"
            liquidacion.depositada_en  = timezone.now()
            liquidacion.depositada_por = request.user
            liquidacion.notas_tesorero = notas
            liquidacion.save(update_fields=[
                "estado", "depositada_en", "depositada_por", "notas_tesorero"
            ])
        messages.success(request, f"Deposito registrado para {liquidacion.vendedor.nombre_completo()}.")
        return redirect("panel_tesorero")

    return render(request, "tesorero/depositar_comision.html", {
        "liquidacion": liquidacion,
    })


@require_role("vendedor")
def mis_comisiones(request):
    """
    El vendedor ve su historial de comisiones acumuladas y liquidaciones.
    """
    vendedor   = request.user
    municipio  = vendedor.municipio

    # Total historico de comisiones generadas (todos los cobros)
    total_acumulado = MovimientoCaja.objects.filter(
        usuario=vendedor,
        tipo="ingreso",
        comision_monto__gt=0,
    ).aggregate(total=Sum("comision_monto"))["total"] or 0

    # Historial de liquidaciones
    liquidaciones = LiquidacionComision.objects.filter(
        vendedor=vendedor,
        municipio=municipio,
    ).order_by("-creado_en")

    return render(request, "vendedores/mis_comisiones.html", {
        "total_acumulado": total_acumulado,
        "liquidaciones":   liquidaciones,
    })


@require_role("vendedor")
def certificar_comision(request, liquidacion_id):
    """
    El vendedor certifica que recibio correctamente su comision depositada.
    Solo puede certificar liquidaciones en estado 'depositada'.
    """
    vendedor    = request.user
    liquidacion = get_object_or_404(
        LiquidacionComision,
        id=liquidacion_id,
        vendedor=vendedor,
    )

    if liquidacion.estado != "depositada":
        messages.warning(request, "Esta liquidacion no esta lista para certificar.")
        return redirect("mis_comisiones")

    if request.method == "POST":
        with transaction.atomic():
            liquidacion.estado        = "certificada"
            liquidacion.certificada_en = timezone.now()
            liquidacion.save(update_fields=["estado", "certificada_en"])
        messages.success(request, "Comision certificada correctamente.")
        return redirect("mis_comisiones")

    return render(request, "vendedores/certificar_comision.html", {
        "liquidacion": liquidacion,
    })
