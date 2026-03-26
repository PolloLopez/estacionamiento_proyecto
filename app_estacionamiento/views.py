# ESTACIONAMIENTO_APP/app_estacionamiento/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.views import LoginView
from django.utils import timezone
from django.urls import reverse

from decimal import Decimal

from .models import Usuario, Vehiculo, Subcuadra, Estacionamiento, Infraccion
from .factories import EstacionamientoFactory
from .decorators import require_role, require_login

def get_subcuadra_default(municipio):
    return Subcuadra.objects.get_or_create(
        calle="Zona Única",
        altura=0,
        municipio=municipio
    )[0]

def get_usuario(request):
    if not request.usuario:
        raise Exception("Usuario no autenticado")
    return request.usuario

def inicio(request):
    usuario = request.usuario

    if not usuario:
        return redirect("login")

    if usuario.es_admin:
        return redirect("panel_admin")
    elif usuario.es_inspector:
        return redirect("panel_inspectores")
    elif usuario.es_vendedor:
        return redirect("panel_vendedores")
    elif usuario.es_conductor:
        return redirect("inicio_usuarios")
    else:
        return redirect("login")


def login_view(request):
    if request.method == "POST":
        correo = request.POST.get("username")  # tu form usa "username"
        password = request.POST.get("password")

        try:
            usuario = Usuario.objects.get(correo=correo)
        except Usuario.DoesNotExist:
            return render(request, "usuarios/login.html", {"form": {"errors": True}})

        if usuario.check_password(password):
            # Guardamos el usuario en la sesión 
            request.session["usuario_id"] = usuario.id
            return redirect("inicio")
        else:
            return render(request, "usuarios/login.html", {"form": {"errors": True}})

    return render(request, "usuarios/login.html")

@require_role("inspector", "admin", "conductor", "vendedor")
def inicio_usuarios(request):
    usuario = request.usuario

    estacionamientos = Estacionamiento.objects.filter(
        registrado_por=usuario,
        activo=True,
        subcuadra__municipio=usuario.municipio
    )

    return render(request, "usuarios/inicio_usuarios.html", {
        "usuario": usuario,
        "estacionamientos": estacionamientos,
    })


# =========================================================
# VIEWS ADMIN
# =========================================================
@require_role("admin")
def panel_admin(request):
    usuario = request.usuario

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
def cargar_saldo(request, usuario_id):
    admin = get_usuario(request)  # quien ejecuta
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

@require_role("admin")
def gestionar_exenciones(request):
    usuario = request.usuario

    vehiculos = Vehiculo.objects.all()
    subcuadras = Subcuadra.objects.filter(municipio=usuario.municipio)

    if request.method == "POST":
        patente = request.POST.get("patente")
        exento_global = request.POST.get("exento_global") == "on"
        subcuadras_ids = request.POST.getlist("subcuadras")

        vehiculo = Vehiculo.objects.filter(patente=patente).first()

        if vehiculo:
            vehiculo.exento_global = exento_global
            vehiculo.save()

            vehiculo.subcuadras_exentas.set(subcuadras_ids)

    return render(request, "admin/exenciones.html", {
        "vehiculos": vehiculos,
        "subcuadras": subcuadras
    })

# =========================================================
# VIEWS USUARIOS
# =========================================================

def home(request):
    """
    Vista principal del sistema.
    - Si hay usuario logueado, redirige al inicio de usuarios.
    - Si no hay sesión, muestra login.
    """
    if not request.session.get("usuario_id"):
        # antes: return redirect("login")
        return render(request, "usuarios/login.html")
    return redirect("inicio_usuarios")

@require_role("conductor")
def estacionar_vehiculo(request):
    usuario = request.usuario

    if request.method == 'POST':
        patente = request.POST.get('patente')
        duracion = request.POST.get('duracion')

        vehiculo, _ = Vehiculo.objects.get_or_create(patente=patente)

        if vehiculo.exento_global or vehiculo.subcuadras_exentas.exists():
            return render(request, 'usuarios/estacionar_vehiculo.html', {
                'error': 'Este vehículo está marcado como exento.'
            })

        if usuario.es_conductor and vehiculo not in usuario.vehiculos.all():
            usuario.vehiculos.add(vehiculo)

        if Estacionamiento.objects.filter(vehiculo=vehiculo, activo=True).exists():
            return render(request, 'usuarios/estacionar_vehiculo.html', {
                'error': 'El vehículo ya tiene un estacionamiento activo.'
            })

        try:
            duracion = Decimal(duracion)
            if duracion <= 0 or duracion % 1 != 0:
                raise ValueError()
        except:
            return render(request, 'usuarios/estacionar_vehiculo.html', {
                'error': 'Duración inválida'
            })

        subcuadra = get_subcuadra_default(usuario.municipio)

        EstacionamientoFactory.crear(vehiculo, subcuadra, duracion, registrado_por=usuario)

        return redirect("inicio_usuarios")

    return render(request, 'usuarios/estacionar_vehiculo.html')
@require_login
def usuarios_historial(request):
    """
    Muestra el historial de estacionamientos del usuario logueado.
    - Si no hay sesión → redirige a login (decorador).
    - Si hay sesión → renderiza historial con estacionamientos.
    """
    usuario = request.usuario

    estacionamientos = Estacionamiento.objects.filter(registrado_por=usuario).order_by("-hora_inicio")

    return render(request, "usuarios/historial_estacionamientos.html", {
        "usuario": usuario,
        "estacionamientos": estacionamientos,
    })

@require_role("conductor")
def finalizar_estacionamiento(request, estacionamiento_id):
    """
    Finaliza un estacionamiento activo del usuario:
    - Si ya está finalizado → redirige al historial.
    - Si no alcanza saldo → redirige al historial sin cerrar.
    - Si alcanza saldo → cierra, descuenta y redirige al historial.
    """
    usuario = request.usuario
    estacionamiento = get_object_or_404(Estacionamiento, id=estacionamiento_id)

    # Si ya está finalizado, volver al historial
    if not estacionamiento.activo:
        return redirect("usuarios_historial_estacionamientos")

    # calcular costo sin cerrar
    costo_final = estacionamiento.finalizar()

    if usuario.saldo < costo_final:
        # ❌ No alcanza saldo → no se finaliza
        return redirect("usuarios_historial_estacionamientos")

    # ✅ Si alcanza saldo → cerrar y descontar
    estacionamiento.hora_fin = timezone.now()
    estacionamiento.costo = costo_final
    estacionamiento.activo = False
    estacionamiento.save()

    usuario.saldo -= costo_final
    usuario.save()

    # redirigir al historial correcto
    return redirect("usuarios_historial_estacionamientos")


@require_role("conductor")
def historial_estacionamientos(request):
    usuario = request.usuario
    estacionamientos = Estacionamiento.objects.filter(
    vehiculo__in=usuario.vehiculos.all(),
    subcuadra__municipio=usuario.municipio
    ).order_by("-hora_inicio")
    return render(request, "usuarios/historial.html", {"estacionamientos": estacionamientos})

@require_role("inspector", "admin")
def usuarios_infracciones(request):
    """
    Muestra historial de infracciones del usuario logueado.
    """
    usuario = request.usuario

    infracciones = Infraccion.objects.filter(vehiculo__usuarios=usuario).order_by("-fecha")

    return render(request, "usuarios/historial_infracciones.html", {
        "usuario": usuario,
        "infracciones": infracciones,
    })


@require_login
def consultar_deuda(request):
    """
    Vista para consultar deuda del usuario.
    """
    return render(request, 'usuarios/consultar_deuda.html')


# =========================================================
# VIEWS INSPECTORES
# =========================================================
@require_role("inspector", "admin")
def panel_inspectores(request):
    usuario = request.usuario

    if not usuario.es_inspector:
        return redirect("inicio")

    return render(request, 'inspectores/panel.html')


#    ============  en test solo @require_login   ============
#              para produccion: @require_role("inspector")

@require_login
def verificar_vehiculo(request):
    usuario = get_usuario(request)
    resultado = None

    if request.method == "POST":
        patente = (request.POST.get("patente") or "").strip().upper()

        if not patente:
            return render(request, "inspectores/verificar_vehiculo.html", {
                "error": "Debe ingresar una patente"
            })
        
        vehiculo = Vehiculo.objects.filter(patente=patente).first()

        # No registrado
        if not vehiculo:
            resultado = {
                "patente": patente,
                "estado": "No registrado",
                "detalle": "Vehículo no registrado",
                "registrar_infraccion_url": reverse("inspectores_registrar_infraccion") + f"?patente={patente}"
            }
            return render(request, "inspectores/verificar_vehiculo.html", {"resultado": resultado})

        # Exento global
        if vehiculo.exento_global:
            resultado = {
                "patente": patente,
                "estado": "Exento",
                "detalle": "Exento total"
            }
            return render(request, "inspectores/verificar_vehiculo.html", {"resultado": resultado})

        estacionamiento = Estacionamiento.objects.filter(
            vehiculo=vehiculo,
            activo=True,
            subcuadra__municipio=usuario.municipio
        ).first()

        # Exento parcial
        if estacionamiento and vehiculo.esta_exento_en(estacionamiento.subcuadra):
            resultado = {
                "patente": patente,
                "estado": "Exento parcial",
                "detalle": "Exento en esta subcuadra",
            }
            return render(request, "inspectores/verificar_vehiculo.html", {"resultado": resultado})

        # Pagado
        if estacionamiento and estacionamiento.costo > 0:
            resultado = {
                "patente": patente,
                "estado": "Pagado",
                "detalle": "Estacionamiento activo"
            }
            return render(request, "inspectores/verificar_vehiculo.html", {"resultado": resultado})

        # Impago
        resultado = {
            "patente": patente,
            "estado": "Impago",
            "detalle": "Estacionamiento sin pago",
            "registrar_infraccion_url": reverse("inspectores_registrar_infraccion") + f"?patente={patente}"
        }
        return render(request, "inspectores/verificar_vehiculo.html", {"resultado": resultado})

    return render(request, "inspectores/verificar_vehiculo.html")

@require_role("inspector")
def registrar_infraccion(request):
    usuario = request.usuario

    if not usuario.es_inspector and not usuario.es_admin:
        return redirect("inicio")

    mensaje = None
    subcuadras = Subcuadra.objects.filter(municipio=usuario.municipio)
    patente = request.GET.get("patente") or request.POST.get("patente")

    if request.method == "POST":
        subcuadra_id = request.POST.get("subcuadra_id")
        foto = request.FILES.get("foto")

        subcuadra = Subcuadra.objects.filter(
            id=subcuadra_id,
            municipio=usuario.municipio
        ).first()

        vehiculo = Vehiculo.objects.filter(patente=patente).first()

        estacionamiento = Estacionamiento.objects.filter(
            vehiculo=vehiculo,
            activo=True,
            subcuadra__municipio=usuario.municipio
        ).first() if vehiculo else None

        if not vehiculo:
            mensaje = f"⚠️ No se encontró vehículo con patente {patente}."

        elif vehiculo.exento_global or (
            estacionamiento and estacionamiento.subcuadra in vehiculo.subcuadras_exentas.all()
        ):
            mensaje = f"Vehículo {patente} exento. No se registra infracción."

        else:
            Infraccion.objects.create(
                vehiculo=vehiculo,
                inspector=usuario,  # 🔥 FIX
                subcuadra=subcuadra or (estacionamiento.subcuadra if estacionamiento else None),
                estacionamiento=estacionamiento,
                fecha=timezone.now(),
                foto=foto
            )
            mensaje = f"🚨 Infracción registrada para {patente}."

    return render(request, "inspectores/registrar_infraccion.html", {
        "mensaje": mensaje,
        "subcuadras": subcuadras,
        "patente": patente,
    })

@require_role("inspector", "admin", "vendedor")
def registrar_estacionamiento_manual(request):
    inspector = get_usuario(request)

    if request.method == "POST":
        patente = request.POST.get("patente")
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
        except:
            return render(request, "inspectores/registrar_estacionamiento_manual.html", {
                "error": "La duración debe ser en horas (ej: 1, 2)."
            })

        subcuadra = get_subcuadra_default(inspector.municipio)
        EstacionamientoFactory.crear(vehiculo, subcuadra, duracion, registrado_por=inspector)

        return redirect("inspectores_verificar_vehiculo")

    return render(request, "inspectores/registrar_estacionamiento_manual.html")

@require_role("vendedor")
def registrar_estacionamiento_vendedor(request):
    vendedor = get_usuario(request)

    if request.method == "POST":
        patente = request.POST.get("patente")
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
    usuario = request.usuario

    if not usuario.es_inspector:
        return redirect("inicio")

    return render(request, 'inspectores/resumen_cobros.html')

@require_role("inspector", "admin")
def resumen_infracciones(request):
    """
    Vista de resumen de infracciones registradas por inspectores.
    - Solo accesible a inspectores.
    """
    usuario = request.usuario
    if not usuario.es_inspector:
        return redirect("inicio")
    return render(request, 'inspectores/resumen_infracciones.html')


# =========================================================
# VIEWS VENDEDORES
# =========================================================
@require_role("vendedor", "admin")
def panel_vendedores(request):
    """
    Panel principal de vendedores.
    - Solo accesible a vendedores.
    """
    usuario = request.usuario
    if not usuario.es_vendedor:
        return redirect("inicio")
    return render(request, 'vendedores/panel.html', {"vendedor": usuario})


@require_role("vendedor", "admin")
def resumen_caja(request):
    usuario = request.usuario

    registros = Estacionamiento.objects.filter(registrado_por=usuario).order_by("-hora_inicio")

    return render(request, 'vendedores/resumen_caja.html', {"registros": registros})

# =========================================================
# VIEWS LOGIN / LOGOUT


def logout_view(request):
    """
    - Cierra sesión del usuario.
    - Redirige al login.
    """
    request.session.flush()
    return render(request, "usuarios/login.html", {"error": "Debe iniciar sesión"})
