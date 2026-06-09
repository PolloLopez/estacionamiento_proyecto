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


@require_role("inspector", "admin", "conductor", "vendedor") 
def inicio_usuarios(request):
    usuario = request.user

    estacionamiento_activo = Estacionamiento.objects.filter(
        usuario=usuario,
        estado="ACTIVO"
    ).order_by("-hora_inicio").first()

    return render(request, "usuarios/inicio_usuarios.html", {
        "usuario": usuario,
        "estacionamiento_activo": estacionamiento_activo,
    })

# =========================================================
# VIEWS USUARIOS
# =========================================================

def home(request):
    if not request.user:
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

@require_role("admin","inspector","vendedor")
def pagar_infraccion(request, infraccion_id):
    infraccion = get_object_or_404(Infraccion, id=infraccion_id)
    try:
        pagar_infraccion_uc(request.user, infraccion)
        messages.success(request, "Infracción cobrada.")
    except Exception as e:
        messages.error(request, str(e))
    return redirect("gestion_infracciones")

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

    return render(request, "admin/panel_admin.html", {
        "inspectores": inspectores,
        "vendedores": vendedores,
        "usuarios": usuarios,
        "estacionamientos": estacionamientos,
        "estacionamientos_activos": estacionamientos_activos,
        "infracciones_recientes": infracciones_recientes,
        "rol_seleccionado": rol,
        "total_cobrado": total_cobrado,
    })

@require_role("admin")
def dashboard_admin(request):

    # 🚨 Infracciones por inspector
    infracciones_por_inspector = Infraccion.objects.values(
        "inspector__correo"
    ).annotate(
        total=Count("id")
    ).order_by("-total")

    # 🚗 Patentes por día
    patentes_por_dia = Vehiculo.objects.annotate(
        fecha=TruncDate("fecha_creacion")  # o created_at
    ).values("fecha").annotate(
        total=Count("id")
    )

    # 💰 Cobros por usuario (inspectores + kioscos)
    cobros = MovimientoCaja.objects.values(
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

    # Si viene ?patente=XYZ desde detalle_usuario, pre-buscamos el vehículo
    patente_get = request.GET.get("patente", "").strip().upper()
    if patente_get and not accion:
        vehiculo = Vehiculo.objects.filter(patente=patente_get).first()

    # 🔎 BUSCAR
    if request.method == "POST" and accion == "buscar":
        #patente = (input).strip().upper()
        patente = (request.POST.get('patente') or "").strip().upper()
        vehiculo = Vehiculo.objects.filter(patente=patente).first()

    # 💾 GUARDAR
    elif request.method == "POST" and accion == "guardar":
        #patente = (input).strip().upper()
        patente = (request.POST.get('patente') or "").strip().upper()
        vehiculo = Vehiculo.objects.filter(patente=patente).first()

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

    return render(request, "admin/exenciones.html", {
        "vehiculo": vehiculo,
        "subcuadras": subcuadras,
        "tipos_exencion": TIPOS_EXENCION,
    })

@require_role("admin")
def cargar_saldo(request, usuario_id):
    admin = request.user
    usuario = get_object_or_404(Usuario, id=usuario_id)

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

    if request.method == "POST":
        patente = request.POST.get("patente", "").strip().upper()

        if not patente:
            return redirect("inicio")

        vehiculo, _ = Vehiculo.objects.get_or_create(patente=patente)

        VehiculoUsuario.objects.get_or_create(
            usuario=request.user,
            vehiculo=vehiculo
        )

        return redirect(
            reverse("usuarios_estacionar_vehiculo")
            + f"?patente={vehiculo.patente}"
        )

    return redirect("usuarios_estacionar_vehiculo")


@require_login
def eliminar_vehiculo(request, vehiculo_id):
    """El conductor desvincula un vehículo de su cuenta (no lo elimina del sistema)."""
    if request.method == "POST":
        VehiculoUsuario.objects.filter(
            usuario=request.user,
            vehiculo_id=vehiculo_id
        ).delete()
    return redirect("usuarios_estacionar_vehiculo")

    return render(request, "usuarios/agregar_vehiculo.html")

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
            vehiculo = Vehiculo.objects.get(id=vehiculo_id)
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
        # 6. DURACIÓN
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
    tarifa_hora = tarifa_obj.precio_por_hora if tarifa_obj else 100

    # Patente preseleccionada (viene del flujo agregar_vehiculo)
    patente_preseleccionada = request.GET.get("patente", "").strip().upper()

    return render(request, "usuarios/estacionar_vehiculo.html", {
        "vehiculos": vehiculos,
        "usuario": usuario,
        "tarifa_hora": tarifa_hora,
        "patente_preseleccionada": patente_preseleccionada,
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
        # duracion_min almacena horas (pese al nombre) — no dividir por 60
        duracion_horas = estacionamiento.duracion_min
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
    # Mostrar solo infracciones de vehículos vinculados a esta cuenta
    # (funciona para conductores registrados Y usuarios que entraron con Google)
    infracciones = (
        Infraccion.objects
        .filter(vehiculo__vehiculousuario__usuario=request.user)
        .distinct()
        .order_by("-creado_en")
    )

    return render(
        request,
        "usuarios/historial_infracciones.html",
        {"infracciones": infracciones}
    )

@require_login
def consultar_deuda(request):

    return render(request, 'usuarios/consultar_deuda.html')

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

    if request.method == "POST":
        patente = (request.POST.get("patente") or "").upper().strip()

        if patente:
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
            infraccion = crear_infraccion(
                patente=patente,
                subcuadra_id=request.POST.get("subcuadra_id"),
                inspector=usuario,
                foto=request.FILES.get("foto")
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
    infraccion = Infraccion.objects.get(id=infraccion_id)

    return render(request, "ticket_infraccion.html", {
        "patente": infraccion.vehiculo.patente,
        "subcuadra": infraccion.subcuadra,
        "fecha": infraccion.creado_en,
        "inspector": infraccion.inspector.correo
    })

@require_role("inspector")
def caja_inspector(request):

    inspector = request.user
    municipio = getattr(inspector, "municipio", None)
    if not municipio:
        return redirect("login")

    movimientos = MovimientoCaja.objects.filter(
        usuario=inspector
    ).order_by("-creado_en")

    total_ingresos = movimientos.filter(tipo="ingreso").aggregate(
        total=Sum("monto"))["total"] or 0
    total_egresos = movimientos.filter(tipo="egreso").aggregate(
        total=Sum("monto"))["total"] or 0

    movimientos_pendientes = movimientos.filter(tipo="ingreso", cerrado=False)
    total_a_cerrar = movimientos_pendientes.aggregate(
        total=Sum("monto"))["total"] or 0

    return render(request, "inspectores/caja.html", {
        "movimientos": movimientos,
        "ingresos": total_ingresos,
        "egresos": total_egresos,
        "saldo": total_ingresos - total_egresos,
        "movimientos_abiertos": movimientos_pendientes.count(),
        "total_a_cerrar": total_a_cerrar,
    })

# =========================================================
# VIEWS COMPARTIDAS INSPECTORES + VENDEDORES
# =========================================================
@require_role("vendedor", "inspector", "admin")
def registrar_estacionamiento_manual(request):
    inspector = request.user

    if request.method == "POST":

        patente = (request.POST.get('patente') or "").strip().upper()
        duracion = request.POST.get("duracion")

        vehiculo, _ = Vehiculo.objects.get_or_create(
            patente=patente,
            defaults={"municipio": inspector.municipio}
        )

        # Asignar municipio si el vehículo no lo tiene
        if not vehiculo.municipio:
            vehiculo.municipio = inspector.municipio
            vehiculo.save()

        # Bloquear cobro manual a vehículos exentos
        if getattr(vehiculo, "exento_global", False):
            return render(request, "inspectores/registrar_estacionamiento_manual.html", {
                "error": f"El vehículo {patente} tiene exención total — no se puede cobrar."
            })

        if Estacionamiento.objects.filter(
            vehiculo=vehiculo,
            estado="ACTIVO"
        ).exists():
            return render(request, "inspectores/registrar_estacionamiento_manual.html", {
                "error": "El vehículo ya tiene un estacionamiento activo."
            })

        try:
            duracion = Decimal(duracion)
            if duracion <= 0 or duracion % 1 != 0:
                raise ValueError()
        except Exception:
            return render(request, "inspectores/registrar_estacionamiento_manual.html", {
                "error": "La duración debe ser en horas (ej: 1, 2)."
            })

        # Tarifa desde el modelo (si no hay, usamos 100 como fallback)
        from app_estacionamiento.models import Tarifa
        tarifa_obj = Tarifa.objects.filter(municipio=inspector.municipio).first()
        tarifa = tarifa_obj.precio_por_hora if tarifa_obj else Decimal("100")
        monto = duracion * tarifa

        subcuadra = get_subcuadra_default(inspector.municipio)

        if not subcuadra:
            return render(request, "inspectores/registrar_estacionamiento_manual.html", {
                "error": "No hay subcuadra configurada para este municipio."
            })

        with transaction.atomic():
            # 1. Crear el estacionamiento (para que luego no aparezca como impago)
            EstacionamientoFactory.crear(
                usuario=inspector,
                vehiculo=vehiculo,
                subcuadra=subcuadra,
                duracion=duracion,
                costo_base=monto
            )

            # 2. Registrar el ingreso en caja del inspector
            cobrar_estacionamiento(
                inspector=inspector,
                monto=monto,
                descripcion=f"Cobro manual {vehiculo.patente}"
            )

        return redirect("panel_inspectores")

    return render(request, "inspectores/registrar_estacionamiento_manual.html")

@require_role("vendedor", "inspector", "admin")
def registrar_estacionamiento_vendedor(request):
    vendedor = request.user

    if request.method == "POST":
        #patente = (input).strip().upper()
        patente = (request.POST.get('patente') or "").strip().upper()
        duracion = request.POST.get("duracion")
        cliente_email = request.POST.get("cliente_email", "").strip()

        # Buscar o crear vehículo
        vehiculo, _ = Vehiculo.objects.get_or_create(patente=patente)

        # Asociar vehículo al cliente (si existe y si es ManyToMany)
        if cliente_email:
            cliente = Usuario.objects.filter(correo=cliente_email).first()
            if cliente:
                # si la relación es ManyToMany
                if hasattr(cliente, "vehiculos"):
                    cliente.vehiculos.add(vehiculo)

        # Validar que no tenga estacionamiento activo
        if Estacionamiento.objects.filter(
            vehiculo=vehiculo,
            estado="ACTIVO"
        ).exists():
            return render(request, "vendedores/registrar_estacionamiento.html", {
                "error": "El vehículo ya tiene un estacionamiento activo."
            })

        # Validar duración (múltiplos de 1 hora; usa (duracion*2)%1 != 0 si querés medias horas)
        try:
            duracion = Decimal(duracion)
            if duracion <= 0 or duracion % 1 != 0:
                raise ValueError("Duración inválida")
        except Exception:
            return render(request, "vendedores/registrar_estacionamiento.html", {
                "error": "La duración debe ser en pasos de horas (ej: 1, 2)."
            })

        # Subcuadra única
        subcuadra = get_subcuadra_default(vendedor.municipio)

        result = ejecutar_estacionamiento(
            vendedor,
            vehiculo,
            subcuadra,
            duracion
        )

        if not result["ok"]:
            return render(request, "vendedores/registrar_estacionamiento.html", {
                "error": "No se pudo registrar estacionamiento"
            })

        return redirect("vendedores_resumen_caja")

    return render(request, "vendedores/registrar_estacionamiento.html")

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
    est = Estacionamiento.objects.get(id=est_id)

    return render(request, "ticket.html", {
        "patente": est.vehiculo.patente,
        "duracion": est.duracion_min,
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
# VIEWS VENDEDORES
# =========================================================
@require_role("vendedor")
def panel_vendedor(request):

    user = request.user

    movimientos = MovimientoCaja.objects.filter(usuario=user)

    total = movimientos.aggregate(total=Sum("monto"))["total"] or 0

    return render(request, "vendedores/panel.html", {
        "movimientos": movimientos,
        "total": total
    })

@require_role("vendedor", "admin")
def resumen_caja(request):
    usuario = request.user

    registros = Estacionamiento.objects.filter(usuario=usuario).order_by("-hora_inicio")

    return render(request, 'vendedores/resumen_caja.html', {"registros": registros})

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

    return redirect("panel_inspectores")

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
            inspector = Usuario.objects.create_user(
                correo=correo,
                password=password,
                municipio=municipio,
                es_inspector=True,
                es_conductor=False,
            )
            inspector.first_name = nombre
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
    inspector = get_object_or_404(Usuario, id=inspector_id, es_inspector=True)

    if request.method == "POST":
        inspector.first_name = request.POST.get("nombre", "").strip()
        inspector.is_active = request.POST.get("activo") == "on"

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
            vendedor = Usuario.objects.create_user(
                correo=correo,
                password=password,
                municipio=municipio,
                es_vendedor=True,
                es_conductor=False,
            )
            vendedor.first_name = nombre
            vendedor.save()
            return redirect("gestionar_vendedores")

    vendedores = Usuario.objects.filter(es_vendedor=True, municipio=municipio)
    return render(request, "admin/gestionar_vendedores.html", {
        "vendedores": vendedores,
        "error": error,
    })

@require_role("admin")
def editar_vendedor(request, vendedor_id):
    vendedor = get_object_or_404(Usuario, id=vendedor_id, es_vendedor=True)

    if request.method == "POST":
        vendedor.first_name = request.POST.get("nombre", "").strip()
        vendedor.is_active = request.POST.get("activo") == "on"
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
            QueryQ(correo__icontains=q) | QueryQ(first_name__icontains=q)
        )

    return render(request, "admin/gestionar_usuarios.html", {
        "usuarios": usuarios,
        "q": q,
    })

@require_role("admin")
def detalle_usuario_admin(request, usuario_id):
    """Vista de detalle de un conductor: saldo, vehículos, exenciones, historial."""
    conductor = get_object_or_404(Usuario, id=usuario_id, es_conductor=True)
    vehiculos = Vehiculo.objects.filter(vehiculousuario__usuario=conductor)

    # Agregar vehículo desde admin
    mensaje = None
    if request.method == "POST" and request.POST.get("accion") == "agregar_vehiculo":
        patente = (request.POST.get("patente") or "").strip().upper()
        if patente:
            vehiculo, _ = Vehiculo.objects.get_or_create(patente=patente)
            VehiculoUsuario.objects.get_or_create(usuario=conductor, vehiculo=vehiculo)
            mensaje = f"Vehículo {patente} agregado."
            vehiculos = Vehiculo.objects.filter(vehiculousuario__usuario=conductor)

    return render(request, "admin/detalle_usuario.html", {
        "conductor": conductor,
        "vehiculos": vehiculos,
        "mensaje": mensaje,
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

    # Acción POST: anular infracción
    if request.method == "POST":
        accion = request.POST.get("accion")
        infraccion_id = request.POST.get("infraccion_id")
        if accion == "anular" and infraccion_id:
            inf = get_object_or_404(Infraccion, id=infraccion_id, municipio=municipio)
            if inf.estado == "pendiente":
                inf.estado = "anulada"
                inf.save()
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
    usuario = request.user
    municipio = usuario.municipio
    from app_estacionamiento.models import Tarifa

    error = None
    if request.method == "POST":
        precio_str = request.POST.get("precio_por_hora", "").strip()
        try:
            precio = Decimal(precio_str)
            if precio <= 0:
                raise ValueError("El precio debe ser mayor a 0.")
            Tarifa.objects.update_or_create(
                municipio=municipio,
                defaults={"precio_por_hora": precio}
            )
            return redirect("gestionar_tarifas")
        except Exception as e:
            error = f"Error al guardar: {e}"

    tarifa_actual = Tarifa.objects.filter(municipio=municipio).first()
    return render(request, "admin/gestionar_tarifas.html", {
        "tarifa_actual": tarifa_actual,
        "error": error,
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


# =========================================================
# VIEWS LOGIN / LOGOUT
# =========================================================
# =========================================================
# VIEWS LOGIN / LOGOUT
# =========================================================
def logout_view(request):
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
    base_url = request.build_absolute_uri("/").rstrip("/")

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
        "auto_return": "approved",
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

    # En sandbox usamos sandbox_init_point; en prod usamos init_point
    if settings.DEBUG:
        checkout_url = resultado["response"]["sandbox_init_point"]
    else:
        checkout_url = resultado["response"]["init_point"]

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
        messages.success(request, f"✅ Se acreditaron ${monto} a tu saldo.")
    except Exception:
        # Si ya fue acreditado por el webhook, está bien
        pass

    # Refrescar saldo desde la DB
    request.user.refresh_from_db()

    return render(request, "usuarios/mp_resultado.html", {
        "estado": "exitoso",
        "monto": monto,
        "saldo_nuevo": request.user.saldo,
    })


@require_login
def mp_fallido(request):
    messages.error(request, "El pago fue rechazado. Podes intentarlo de nuevo.")
    return render(request, "usuarios/mp_resultado.html", {"estado": "fallido"})


@require_login
def mp_pendiente(request):
    messages.warning(request, "El pago esta pendiente de acreditacion. Te avisaremos cuando se confirme.")
    return render(request, "usuarios/mp_resultado.html", {"estado": "pendiente"})


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

    # Recuperamos usuario y monto desde los metadatos
    try:
        metadata = info.get("metadata", {})
        usuario_id = metadata.get("usuario_id")
        monto = Decimal(str(metadata.get("monto", 0)))
        usuario = Usuario.objects.get(pk=usuario_id)
    except Exception:
        return HttpResponse(status=200)

    try:
        acreditar(usuario, monto, payment_id)
    except Exception:
        pass  # Si ya fue acreditado (idempotencia) no hay problema

    return HttpResponse(status=200)
