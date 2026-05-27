# ESTACIONAMIENTO_APP/app_estacionamiento/views.py

from logging import warning
from urllib import request

from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.contrib.auth import authenticate, login, logout
from django.urls import reverse
from decimal import Decimal
from django.db import IntegrityError, transaction
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
    CierreCaja
)

from .utils import get_subcuadra_default
from .factories import EstacionamientoFactory
from datetime import timedelta
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from app_estacionamiento.services_verificacion import verificar_estado_vehiculo
from app_estacionamiento.services_infracciones import crear_infraccion, ErrorInfraccion

@require_role("inspector", "admin", "conductor", "vendedor") 
def inicio_usuarios(request):
    usuario = request.user

    estacionamiento_activo = Estacionamiento.objects.filter(
    activo=True,
    registrado_por=usuario
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

    if usuario.es_inspector:
        return redirect("panel_inspectores")

    if usuario.es_vendedor:
        return redirect("panel_vendedores")

    if usuario.es_conductor:
        return redirect("inicio_usuarios")

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

            # 🏛️ Municipio por defecto
            usuario.municipio = Municipio.objects.first()

            usuario.save()

            # 🔐 Login automático
            login(request, usuario)

            # 🔥 REDIRECCIÓN POR ROL
            return redirect_por_rol(usuario)

    else:
        form = RegistroUsuarioForm()

    return render(request, "usuarios/registro.html", {
        "form": form
    })

# =========================================================
# VIEWS ADMIN
# =========================================================
@require_role("admin")
def panel_admin(request):
    usuario = request.user

    inspectores = Usuario.objects.filter(es_inspector=True, municipio=usuario.municipio)
    vendedores = Usuario.objects.filter(es_vendedor=True, municipio=usuario.municipio)
    usuarios = Usuario.objects.filter(es_conductor=True, municipio=usuario.municipio)

    rol = request.GET.get("rol")

    estacionamientos = Estacionamiento.objects.select_related(
        "vehiculo", "subcuadra", "registrado_por"
    ).filter(subcuadra__municipio=usuario.municipio)

    if rol == "vendedor":
        estacionamientos = estacionamientos.filter(registrado_por__in=vendedores)
    elif rol == "inspector":
        estacionamientos = estacionamientos.filter(registrado_por__in=inspectores)
    elif rol == "conductor":
        estacionamientos = estacionamientos.filter(registrado_por__in=usuarios)

    estacionamientos = estacionamientos.order_by("-hora_inicio")

    estacionamientos_activos = Estacionamiento.objects.filter(
        activo=True,
        subcuadra__municipio=usuario.municipio
    ).count()

    infracciones_recientes = Infraccion.objects.filter(
        subcuadra__municipio=usuario.municipio
    ).order_by('-fecha')[:5]

    return render(request, "admin/panel_admin.html", {
        "inspectores": inspectores,
        "vendedores": vendedores,
        "usuarios": usuarios,
        "estacionamientos": estacionamientos,
        "estacionamientos_activos": estacionamientos_activos,
        "infracciones_recientes": infracciones_recientes,
        "rol_seleccionado": rol,
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

    return render(request, "admin/dashboard.html", {
        "infracciones_por_inspector": infracciones_por_inspector,
        "patentes_por_dia": patentes_por_dia,
        "cobros": cobros
    })

@require_role("admin")
def panel_exenciones(request):
    usuario = request.user

    vehiculo = None
    subcuadras = Subcuadra.objects.filter(municipio=usuario.municipio)

    accion = request.POST.get("accion")

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
            vehiculo.save()

            subcuadras_ids = request.POST.getlist("subcuadras")
            vehiculo.subcuadras_exentas.set(subcuadras_ids)

    return render(request, "admin/exenciones.html", {
        "vehiculo": vehiculo,
        "subcuadras": subcuadras
    })

@require_role("admin")
def cargar_saldo(request, usuario_id):
    admin = request.user  # quien ejecuta
    usuario = get_object_or_404(Usuario, id=usuario_id)  # a quién le cargo saldo

    if request.method == "POST":
        monto = request.POST.get("monto")
        try:
            monto = Decimal(monto)
            usuario.saldo += monto
            usuario.save()
            return redirect("panel_admin")
        except ValueError:
            return render(request, "admin/cargar_saldo.html", {
                "usuario": usuario,
                "error": "Monto inválido"
            })

    return render(request, "admin/cargar_saldo.html", {"usuario": usuario})

@login_required
def agregar_vehiculo(request):

    if request.method == "POST":
        patente = request.POST.get("patente", "").strip().upper()

        if not patente:
            return redirect("inicio_usuarios")

        vehiculo, _ = Vehiculo.objects.get_or_create(patente=patente)

        VehiculoUsuario.objects.get_or_create(
            usuario=request.user,
            vehiculo=vehiculo
        )

        return redirect("inicio_usuarios")

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
        # 4. WARNINGS (mejorados)
        # =============================================

        warnings_list = []

        relaciones = VehiculoUsuario.objects.filter(vehiculo=vehiculo)

        if relaciones.filter(es_propietario=True).exists() and not relaciones.filter(usuario=usuario, es_propietario=True).exists():
            warnings_list.append("🚨 Este vehículo tiene otro propietario")

        if relaciones.exclude(usuario=usuario).exists():
            warnings_list.append("⚠️ Vehículo asociado a múltiples usuarios")

        if not relacion.verificado:
            warnings_list.append("⛔ Usuario no verificado")

        warning = " | ".join(warnings_list) if warnings_list else None

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
            activo=True
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

        TARIFA_BASE = Decimal("100")
        costo_estimado = duracion * TARIFA_BASE

        if usuario.saldo < costo_estimado:
            return render(request, "usuarios/estacionar_vehiculo.html", {
                "error": f"Saldo insuficiente. Necesitás ${costo_estimado}",
                "warning": warning,
                "vehiculos": vehiculos,
                "usuario": usuario
            })

        # =============================================
        # 8. TRANSACCIÓN
        # =============================================

        subcuadra = get_subcuadra_default(usuario.municipio)

        try:
            with transaction.atomic():

                usuario = Usuario.objects.select_for_update().get(id=usuario.id)

                if usuario.saldo < costo_estimado:
                    return render(request, "usuarios/estacionar_vehiculo.html", {
                        "error": f"Saldo insuficiente. Necesitás ${costo_estimado}",
                        "warning": warning,
                        "vehiculos": vehiculos,
                        "usuario": usuario
                    })

                EstacionamientoFactory.crear(
                    vehiculo,
                    subcuadra,
                    duracion,
                    registrado_por=usuario
                )

                usuario.saldo -= costo_estimado
                usuario.save()

        except IntegrityError:
            return render(request, "usuarios/estacionar_vehiculo.html", {
                "error": "El vehículo ya posee un estacionamiento activo.",
                "warning": warning,
                "vehiculos": vehiculos,
                "usuario": usuario
            })

        except Exception:
            return render(request, "usuarios/estacionar_vehiculo.html", {
                "error": "Ocurrió un error al registrar el estacionamiento.",
                "warning": warning,
                "vehiculos": vehiculos,
                "usuario": usuario
            })

        # ✅ CORRECTO
        return redirect("inicio")

    # =================================================
    # GET
    # =================================================

    return render(request, "usuarios/estacionar_vehiculo.html", {
        "vehiculos": vehiculos,
        "usuario": usuario
    })

@require_role("conductor", "vendedor", "admin")
def cargar_saldo(request):

    return render(
        request,
        "usuarios/cargar_saldo.html"
    )
    
@require_login
def usuarios_historial(request):
    usuario = request.user

    estacionamientos = Estacionamiento.objects.filter(
        registrado_por=usuario
        ).order_by("-hora_inicio")

    return render(request, "usuarios/historial_estacionamientos.html", {
        "usuario": usuario,
        "estacionamientos": estacionamientos,
    })

@require_role("conductor")
def finalizar_estacionamiento(request, estacionamiento_id):
    usuario = request.user
    estacionamiento = get_object_or_404(Estacionamiento, id=estacionamiento_id)

    # 🔐 SOLO EL QUE LO CREÓ
    if estacionamiento.registrado_por != usuario:
        return redirect("inicio")

    # Ya finalizado
    if not estacionamiento.activo:
        return redirect("usuarios_historial_estacionamientos")

    # Calcular costo sin cerrar (preview)
    costo_estimado = estacionamiento.calcular_costo()

    # ✅ Finalizar correctamente
    costo_final = estacionamiento.finalizar()

    usuario.saldo -= costo_final
    usuario.save()

    return redirect("usuarios_historial_estacionamientos")

@require_role("conductor")
def historial_estacionamientos(request):
    usuario = request.user
    estacionamientos = Estacionamiento.objects.filter(
    vehiculo__in=usuario.vehiculos.all(),
    subcuadra__municipio=usuario.municipio
    ).order_by("-hora_inicio")
    return render(request, "usuarios/historial.html", {"estacionamientos": estacionamientos})

@require_role("inspector", "admin")
def usuarios_infracciones(request):

    usuario = request.user

    infracciones = Infraccion.objects.filter(
        municipio=usuario.municipio
    ).select_related("vehiculo", "inspector").order_by("-fecha")

    return render(request, "usuarios/historial_infracciones.html", {
        "usuario": usuario,
        "infracciones": infracciones,
    })

@require_login
def consultar_deuda(request):

    return render(request, 'usuarios/consultar_deuda.html')

# =========================================================
# VIEWS INSPECTORES
# =========================================================
@require_role("inspector")

def panel_inspectores(request):
    usuario = request.user

    # 🚗 NO PAGADOS (simplificado por ahora)
    no_pagados = Estacionamiento.objects.filter(
        activo=False,
        subcuadra__municipio=usuario.municipio
    ).count()

    # 🚨 INFRACCIONES DEL INSPECTOR
    infracciones = Infraccion.objects.filter(
        inspector=usuario
    ).count()

    # 💰 COBRADO (lo que generó en calle)
    total_cobrado = MovimientoCaja.objects.filter(
        usuario=usuario,
        tipo="egreso"
    ).aggregate(total=Sum("monto"))["total"] or 0

    # 💸 GASTADO (opcional si después cargás costos)
    total_gastado = MovimientoCaja.objects.filter(
        usuario=usuario,
        tipo="ingreso"
    ).aggregate(total=Sum("monto"))["total"] or 0

    resumen = {
        "no_pagados": no_pagados,
        "infracciones": infracciones,
        "a_rendir": total_cobrado,
        "saldo_operativo": usuario.saldo_operativo,
        "total_gastado": total_gastado
    }

    return render(request, "inspectores/panel.html", {
        "resumen": resumen
    })


@require_role("inspector", "admin")
def verificar_vehiculo(request):

    if request.method == "GET":
        return render(request, "inspectores/verificar_vehiculo.html", {})

    patente = (request.POST.get("patente") or "").strip().upper()

    if not patente:
        return render(request, "inspectores/verificar_vehiculo.html", {
            "error": "Debe ingresar una patente"
        })

    resultado = verificar_estado_vehiculo(patente, request.user)
    
    return render(request, "inspectores/verificar_vehiculo.html", {
        "resultado": resultado.to_dict()
    })

@require_role("inspector")
def registrar_infraccion(request):
    usuario = request.user
    mensaje = None

    patente = request.GET.get("patente") or request.POST.get("patente")

    if not patente:
        return redirect("inspectores_verificar_vehiculo")

    vehiculo, creado = Vehiculo.objects.get_or_create(
        patente=patente,
        defaults={
            "municipio": usuario.municipio
        }
    )

    subcuadras = Subcuadra.objects.filter(
        municipio=usuario.municipio
    )

    ultima_infraccion = Infraccion.objects.filter(
        inspector=usuario
    ).order_by("-id").first()

    subcuadra_default = ultima_infraccion.subcuadra_id if ultima_infraccion else None

    infracciones_recientes = Infraccion.objects.filter(
        vehiculo=vehiculo
    ).order_by("-id")[:3]

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

    # ==============================
    # 👇 ESTO ES LO QUE TE FALTABA
    # ==============================
    return render(request, "inspectores/registrar_infraccion.html", {
        "mensaje": mensaje,
        "vehiculo": vehiculo,
        "patente": patente,
        "subcuadras": subcuadras,
        "infracciones_recientes": infracciones_recientes,
        "subcuadra_default": subcuadra_default
    })

@require_role("inspector", "admin", "vendedor")
def registrar_estacionamiento_manual(request):
    inspector = request.user

    if request.method == "POST":

        patente = (request.POST.get('patente') or "").strip().upper()
        duracion = request.POST.get("duracion")

        vehiculo, _ = Vehiculo.objects.get_or_create(patente=patente)

        if Estacionamiento.objects.filter(vehiculo=vehiculo, activo=True).exists():
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

        TARIFA = Decimal("100")
        monto = duracion * TARIFA 

        # 🔴 CONTROL DE CAJA
        if inspector.saldo_operativo < monto:
            return render(request, "inspectores/registrar_estacionamiento_manual.html", {
                "error": "No tenés saldo operativo suficiente."
            })

        subcuadra = get_subcuadra_default(inspector.municipio)

        est = EstacionamientoFactory.crear(
            vehiculo,
            subcuadra,
            duracion,
            registrado_por=inspector
        )

        # 💰 descontar saldo operativo
        monto = duracion * TARIFA
        inspector.saldo_operativo -= monto
        inspector.save()

        # 🧾 REGISTRAR MOVIMIENTO DE CAJA
        MovimientoCaja.objects.create(
            usuario=inspector,
            monto=monto,
            tipo="egreso",
            descripcion=f"Cobro estacionamiento {vehiculo.patente}"
        )

        # 👉 mostrar ticket en vez de redirigir
        return redirect("inspectores_ticket_cobro", est.id)
        #return render(request, "ticket.html", {
        #    "patente": vehiculo.patente,
        #    "duracion": duracion,
        #    "hora": est.hora_inicio,
        #    "monto": monto,
        #}, status=200)
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
        if Estacionamiento.objects.filter(vehiculo=vehiculo, activo=True).exists():
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

        # Crear estacionamiento
        EstacionamientoFactory.crear(vehiculo, subcuadra, duracion, registrado_por=vendedor)

        return redirect("vendedores_resumen_caja")

    return render(request, "vendedores/registrar_estacionamiento.html")

@require_role("inspector", "vendedor", "admin")
def resumen_cobros(request):
    usuario = request.user

    if not usuario.es_inspector:
        return redirect("inicio")

    return render(request, 'inspectores/resumen_cobros.html')

@require_role("inspector", "admin", "vendedor")
def ticket_cobro(request, est_id):
    est = Estacionamiento.objects.get(id=est_id)

    return render(request, "ticket.html", {
        "patente": est.vehiculo.patente,
        "duracion": est.duracion,
        "hora": est.hora_inicio,
        "monto": est.duracion * 100  # o tu tarifa
    })

@require_role("inspector", "admin")
def resumen_infracciones(request):
    usuario = request.user

    infracciones = Infraccion.objects.filter(
        municipio=usuario.municipio
    ).select_related("vehiculo", "subcuadra").order_by("-fecha")

    return render(request, "inspectores/resumen_infracciones.html", {
        "infracciones": infracciones
    })

@require_role("inspector")
def ticket_infraccion(request, infraccion_id):
    infraccion = Infraccion.objects.get(id=infraccion_id)

    return render(request, "ticket_infraccion.html", {
        "patente": infraccion.vehiculo.patente,
        "subcuadra": infraccion.subcuadra,
        "fecha": infraccion.fecha,
        "inspector": infraccion.inspector.correo
    })

@require_role("inspector")
def caja_inspector(request):

    inspector = request.user

    movimientos = MovimientoCaja.objects.filter(
        usuario=inspector
    ).order_by("-fecha")

    total_ingresos = movimientos.filter(tipo="ingreso").aggregate(
        total=Sum("monto")
    )["total"] or 0

    total_egresos = movimientos.filter(tipo="egreso").aggregate(
        total=Sum("monto")
    )["total"] or 0

    saldo = total_ingresos - total_egresos

    return render(request, "inspectores/caja.html", {
        "movimientos": movimientos,
        "ingresos": total_ingresos,
        "egresos": total_egresos,
        "saldo": saldo
    })

# =========================================================
# VIEWS VENDEDORES
# =========================================================
@require_role("vendedor", "admin")
def panel_vendedores(request):
    usuario = request.user
    if not usuario.es_vendedor:
        return redirect("inicio")
    return render(request, 'vendedores/panel.html', {"vendedor": usuario})

@require_role("vendedor", "admin")
def resumen_caja(request):
    usuario = request.user

    registros = Estacionamiento.objects.filter(registrado_por=usuario).order_by("-hora_inicio")

    return render(request, 'vendedores/resumen_caja.html', {"registros": registros})

@require_role("inspector")
def cerrar_caja(request):

    usuario = request.user

    # 🧠 último cierre
    ultimo_cierre = CierreCaja.objects.filter(
        usuario=usuario
    ).order_by("-fecha_cierre").first()

    fecha_inicio = ultimo_cierre.fecha_cierre if ultimo_cierre else usuario.date_joined

    # 💰 calcular total
    movimientos = MovimientoCaja.objects.filter(
        usuario=usuario,
        tipo="egreso",
        fecha__gte=fecha_inicio
    )

    total = movimientos.aggregate(total=Sum("monto"))["total"] or 0

    if request.method == "POST":

        cierre = CierreCaja.objects.create(
            usuario=usuario,
            fecha_inicio=fecha_inicio,
            total_cobrado=total
        )

        # 🔥 REGISTRO EN HISTORIAL (MEJORA PRO)
        MovimientoCaja.objects.create(
            usuario=usuario,
            monto=total,
            tipo="cierre",
            descripcion="Cierre de caja inspector"
        )

        return render(request, "inspectores/cierre_exitoso.html", {
            "total": total,
            "cierre": cierre
        })

    return render(request, "inspectores/cerrar_caja.html", {
        "total": total,
        "desde": fecha_inicio
    })

# =========================================================
# VIEWS LOGIN / LOGOUT

def logout_view(request):
    logout(request)
    return redirect("login")