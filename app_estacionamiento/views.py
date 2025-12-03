# ESTACIONAMIENTO_APP/app_estacionamiento/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.views import LoginView
from django.contrib.auth import authenticate, login
from django.utils import timezone
from django.http import HttpResponse
from .models import Usuario, Vehiculo, Subcuadra, Estacionamiento, Infraccion
from .estrategias import EstrategiaExencion
from .factories import EstacionamientoFactory
from decimal import Decimal, ROUND_HALF_UP
from .decorators import require_role, require_login
from app_estacionamiento.decorators import require_role
from app_estacionamiento.models import Vehiculo, Subcuadra, Estacionamiento, Infraccion, Usuario
from app_estacionamiento.estrategias import EstrategiaExencion


def inicio(request):
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return redirect("login")

    usuario = get_object_or_404(Usuario, id=usuario_id)

    if usuario.es_admin:
        return redirect("panel_admin")
    elif usuario.es_inspector:
        return redirect("inspectores_verificar_vehiculo")
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
            # Guardamos el usuario en la sesión (clave que usan tus decoradores)
            request.session["usuario_id"] = usuario.id
            return redirect("inicio_usuarios")
        else:
            return render(request, "usuarios/login.html", {"form": {"errors": True}})

    return render(request, "usuarios/login.html")


@require_role("conductor", "inspector", "vendedor", "admin")
def inicio_usuarios(request):
    usuario_id = request.session.get("usuario_id")
    usuario = get_object_or_404(Usuario, id=usuario_id)

    # Podés pasar estacionamientos activos si querés
    estacionamientos = usuario.estacionamiento_set.filter(activo=True)

    return render(
        request,
        "usuarios/inicio_usuarios.html",
        {"usuario": usuario, "estacionamientos": estacionamientos},
    )
# =========================================================
# VIEWS ADMIN
# =========================================================
@require_role("admin")
def panel_admin(request):
    inspectores = Usuario.objects.filter(es_inspector=True)
    vendedores = Usuario.objects.filter(es_vendedor=True)
    usuarios = Usuario.objects.filter(es_conductor=True)

    # Filtro dinámico por rol
    rol = request.GET.get("rol")
    estacionamientos = Estacionamiento.objects.select_related("vehiculo", "subcuadra", "registrado_por")

    if rol == "vendedor":
        estacionamientos = estacionamientos.filter(registrado_por__in=vendedores)
    elif rol == "inspector":
        estacionamientos = estacionamientos.filter(registrado_por__in=inspectores)
    elif rol == "conductor":
        estacionamientos = estacionamientos.filter(registrado_por__in=usuarios)

    estacionamientos = estacionamientos.order_by("-hora_inicio")

    estacionamientos_activos = Estacionamiento.objects.filter(activo=True).count()
    infracciones_recientes = Infraccion.objects.order_by('-fecha')[:5]

    contexto = {
        "inspectores": inspectores,
        "vendedores": vendedores,
        "usuarios": usuarios,
        "estacionamientos": estacionamientos,
        "estacionamientos_activos": estacionamientos_activos,
        "infracciones_recientes": infracciones_recientes,
        "rol_seleccionado": rol,
    }
    return render(request, "admin/panel_admin.html", contexto)

@require_role("admin")
def cargar_saldo_usuario(request):
    usuario_id = request.session.get("usuario_id")
    usuario = get_object_or_404(Usuario, id=usuario_id)

    if request.method == "POST":
        monto = request.POST.get("monto")
        try:
            monto = float(monto)
            usuario.saldo += monto
            usuario.save()
            return redirect("inicio_usuarios")
        except ValueError:
            return render(request, "usuarios/cargar_saldo.html", {
                "usuario": usuario,
                "error": "Monto inválido"
            })

    return render(request, "usuarios/cargar_saldo.html", {"usuario": usuario})

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
    """
    Vista para registrar un estacionamiento.
    - Conductores: pueden estacionar sus propios vehículos o cualquier patente válida.
    - Inspectores/Admin: pueden estacionar cualquier patente sin restricción.
    - Usa siempre 'Zona Única' como tarifa global.
    """
    # 🔒 Validar sesión
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return render(request, "usuarios/login.html", {"error": "Debe iniciar sesión"})

    usuario = get_object_or_404(Usuario, id=usuario_id)

    # 🔒 Validar rol
    if not (usuario.es_conductor or usuario.es_inspector or usuario.es_admin):
        return redirect("inicio")

    if request.method == 'POST':
        patente = request.POST.get('patente')
        duracion = request.POST.get('duracion')

        # Buscar o crear el vehículo
        vehiculo, _ = Vehiculo.objects.get_or_create(patente=patente)

        # 🚫 Validar exenciones: nunca debe estacionar
        if vehiculo.exento_global or vehiculo.subcuadras_exentas.exists():
            return render(request, 'usuarios/estacionar_vehiculo.html', {
        'error': 'Este vehículo está marcado como exento. No puede estacionar.'
        })

        # Si es conductor, asociar el vehículo a su cuenta
        if usuario.es_conductor and vehiculo not in usuario.vehiculos.all():
            usuario.vehiculos.add(vehiculo)

        # Validar que no tenga estacionamiento activo
        if Estacionamiento.objects.filter(vehiculo=vehiculo, activo=True).exists():
            return render(request, 'usuarios/estacionar_vehiculo.html', {
                'error': 'El vehículo ya tiene un estacionamiento activo.'
            })

        # Validar duración
        try:
            duracion = Decimal(duracion)
            if duracion <= 0 or duracion % 1 != 0:
                raise ValueError("Duración inválida")
        except Exception:
            return render(request, 'usuarios/estacionar_vehiculo.html', {
                'error': 'La duración debe ser en horas (ej: 1, 2).'
            })

        # Subcuadra única
        subcuadra, _ = Subcuadra.objects.get_or_create(calle="Zona Única", altura=0)

        # Crear estacionamiento
        EstacionamientoFactory.crear(vehiculo, subcuadra, duracion, registrado_por=usuario)

        # Redirigir al inicio del conductor
        return redirect("inicio_usuarios")

    return render(request, 'usuarios/estacionar_vehiculo.html')

@require_login
def usuarios_historial(request):
    """
    Muestra el historial de estacionamientos del usuario logueado.
    - Si no hay sesión → redirige a login (decorador).
    - Si hay sesión → renderiza historial con estacionamientos.
    """
    usuario_id = request.session.get("usuario_id")
    usuario = get_object_or_404(Usuario, id=usuario_id)

    estacionamientos = Estacionamiento.objects.filter(registrado_por=usuario).order_by("-hora_inicio")

    return render(request, "usuarios/historial.html", {
        "usuario": usuario,
        "estacionamientos": estacionamientos,
    })


@require_role("conductor")
def finalizar_estacionamiento(request, estacionamiento_id):
    usuario_id = request.session.get("usuario_id")
    usuario = get_object_or_404(Usuario, id=usuario_id)
    estacionamiento = get_object_or_404(Estacionamiento, id=estacionamiento_id)

    if not estacionamiento.activo:
        return redirect("usuarios_historial")

    # calcular costo sin cerrar
    costo_final = estacionamiento.finalizar()

    if usuario.saldo < costo_final:
        # ❌ No alcanza saldo → no se finaliza
        return redirect("usuarios_historial")

    # ✅ Si alcanza saldo → cerrar y descontar
    estacionamiento.hora_fin = timezone.now()
    estacionamiento.costo = costo_final
    estacionamiento.activo = False
    estacionamiento.save()

    usuario.saldo -= costo_final
    usuario.save()
    return redirect("usuarios_historial")


@require_role("inspector", "admin", "conductor")
def historial_estacionamientos(request):
    """
    Muestra historial de estacionamientos del usuario logueado.
    """
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return render(request, "usuarios/login.html", {"error": "Debe iniciar sesión"})
    usuario = get_object_or_404(Usuario, id=usuario_id)

    estacionamientos = Estacionamiento.objects.filter(vehiculo__usuarios=usuario)

    return render(request, 'usuarios/historial.html', {
        'estacionamientos': estacionamientos
    })

@require_role("inspector", "admin")
def historial_infracciones(request):
    """
    Muestra historial de infracciones del usuario logueado.
    """
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return render(request, "usuarios/login.html", {"error": "Debe iniciar sesión"})
    usuario = get_object_or_404(Usuario, id=usuario_id)

    infracciones = Infraccion.objects.filter(vehiculo__usuarios=usuario)

    return render(request, 'usuarios/historial_infracciones.html', {
        'infracciones': infracciones
    })

@require_role("inspector", "admin")
def usuarios_infracciones(request):
    usuario_id = request.session.get("usuario_id")
    usuario = get_object_or_404(Usuario, id=usuario_id)
    infracciones = Infraccion.objects.filter(vehiculo__usuarios=usuario).order_by("-fecha")
    return render(request, "usuarios/historial_infracciones.html", {
        "usuario": usuario,
        "infracciones": infracciones
    })

@require_role("admin")
def cargar_saldo(request, usuario_id):
    """
    Permite al admin cargar saldo a un usuario.
    """
    usuario = get_object_or_404(Usuario, id=usuario_id)

    if request.method == "POST":
        monto = request.POST.get("monto")
        try:
            monto = float(monto)
            usuario.saldo += monto
            usuario.save()
            return redirect("panel_admin")
        except ValueError:
            return render(request, "admin/cargar_saldo.html", {
                "usuario": usuario,
                "error": "Monto inválido"
            })

    return render(request, "admin/cargar_saldo.html", {"usuario": usuario})
    

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
    """
    Panel principal de inspectores.
    - Solo accesible si el usuario es inspector.
    """
    usuario_id = request.session.get("usuario_id")
    usuario = get_object_or_404(Usuario, id=usuario_id)
    if not usuario.es_inspector:
        return redirect("inicio")
    return render(request, 'inspectores/panel.html')


#    ============  en test solo @require_login   ============
#              para produccion: @require_role("inspector")

@require_login
def verificar_vehiculo(request):
    """
    Verifica el estado de un vehículo:
    - Exento global → mensaje directo
    - Exento parcial → listado de subcuadras exentas
    - Pagado → estacionamiento activo con costo > 0
    - Impago → infracción
    """
    resultado = None

    if request.method == "POST":
        patente = (request.POST.get("patente") or "").strip().upper()
        vehiculo = Vehiculo.objects.filter(patente=patente).first()

        if not vehiculo:
            resultado = {"patente": patente, "estado": "No registrado"}
            return render(request, "inspectores/verificar_vehiculo.html", {"resultado": resultado})

        # Caso exento global
        if vehiculo.exento_global:
            resultado = {"patente": patente, "estado": "Exento", "detalle": "Exento en todas las subcuadras"}
            return render(request, "inspectores/verificar_vehiculo.html", {"resultado": resultado})

        # Caso exento parcial
        subcuadras_exentas = vehiculo.subcuadras_exentas.all()
        if subcuadras_exentas.exists():
            resultado = {
                "patente": patente,
                "estado": "Exento parcial",
                "detalle": "Exento en las siguientes subcuadras:",
                "subcuadras": subcuadras_exentas
            }
            return render(request, "inspectores/verificar_vehiculo.html", {"resultado": resultado})

        # Caso con estacionamiento activo
        estacionamiento = Estacionamiento.objects.filter(vehiculo=vehiculo, activo=True).first()
        if estacionamiento and estacionamiento.costo > 0:
            resultado = {"patente": patente, "estado": "Pagado", "detalle": "Estacionamiento activo"}
            return render(request, "inspectores/verificar_vehiculo.html", {"resultado": resultado})

        # Caso impago → infracción
        Infraccion.objects.create(
            vehiculo=vehiculo,
            inspector=request.user if hasattr(request, "user") else None,
            motivo="Impago",
            fecha=timezone.now(),
        )
        resultado = {"patente": patente, "estado": "Impago", "detalle": "Se registró infracción"}
        return render(request, "inspectores/verificar_vehiculo.html", {"resultado": resultado})

    return render(request, "inspectores/verificar_vehiculo.html")

@require_role("inspector", "admin", "vendedor")
def registrar_estacionamiento_manual(request):
    """
    Vista para que un inspector registre un estacionamiento manualmente.
    - Puede registrar cualquier patente.
    - Usa siempre 'Zona Única' como subcuadra global.
    """
    usuario_id = request.session.get("usuario_id")
    inspector = get_object_or_404(Usuario, id=usuario_id)

    if request.method == "POST":
        patente = request.POST.get("patente")
        duracion = request.POST.get("duracion")

        # Buscar o crear vehículo
        vehiculo, _ = Vehiculo.objects.get_or_create(patente=patente)

        # Validar que no tenga estacionamiento activo
        if Estacionamiento.objects.filter(vehiculo=vehiculo, activo=True).exists():
            return render(request, "inspectores/registrar_estacionamiento_manual.html", {
                "error": "El vehículo ya tiene un estacionamiento activo."
            })

        # Validar duración
        try:
            duracion = Decimal(duracion)
            if duracion <= 0 or duracion % 1 != 0:
                raise ValueError("Duración inválida")
        except Exception:
            return render(request, "inspectores/registrar_estacionamiento_manual.html", {
                "error": "La duración debe ser en pasos de horas (ej: 1, 2)."
            })

        # Subcuadra única
        subcuadra, _ = Subcuadra.objects.get_or_create(calle="Zona Única", altura=0)

        # Crear estacionamiento
        EstacionamientoFactory.crear(vehiculo, subcuadra, duracion, registrado_por=inspector)

        return redirect("inspectores_verificar_vehiculo")

    return render(request, "inspectores/registrar_estacionamiento_manual.html")

@require_role("vendedor")
def registrar_estacionamiento_vendedor(request):
    """
    Vista para que un vendedor registre un estacionamiento.
    - Solo accesible a vendedores.
    - Usa siempre 'Zona Única' como subcuadra global.
    """
    usuario_id = request.session.get("usuario_id")
    vendedor = get_object_or_404(Usuario, id=usuario_id)

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
        subcuadra, _ = Subcuadra.objects.get_or_create(calle="Zona Única", altura=0)

        # Crear estacionamiento
        EstacionamientoFactory.crear(vehiculo, subcuadra, duracion, registrado_por=vendedor)

        return redirect("vendedores_resumen_caja")

    return render(request, "vendedores/registrar_estacionamiento.html")

@require_role("inspector")
def registrar_infraccion(request):
    """
    Registrar infracción.
    - Si el vehículo es exento (global o subcuadra) → no se multa.
    - Si no → se crea infracción.
    """
    usuario_id = request.session.get("usuario_id")
    inspector = get_object_or_404(Usuario, id=usuario_id)

    if not inspector.es_inspector and not inspector.es_admin:
        return redirect("inicio")

    mensaje = None
    patente = request.POST.get("patente") or request.GET.get("patente")

    if patente:
        vehiculo = get_object_or_404(Vehiculo, patente=patente)

        if vehiculo.exento_global or vehiculo.subcuadras_exentas.exists():
            mensaje = f"Vehículo {patente} verificado como exento. No se registra infracción."
        else:
            estacionamiento = Estacionamiento.objects.filter(
                vehiculo=vehiculo, activo=True
            ).first()

            Infraccion.objects.create(
                vehiculo=vehiculo,
                inspector=inspector,
                subcuadra=estacionamiento.subcuadra if estacionamiento else None,
                estacionamiento=estacionamiento,
                fecha=timezone.now()
            )
            mensaje = f"Infracción registrada para {patente}."

    return render(request, "inspectores/registrar_infraccion.html", {
        "mensaje": mensaje
    })

@require_role("inspector", "vendedor", "admin")
def resumen_cobros(request):
    """
    Vista de resumen de cobros realizados por inspectores.
    - Solo accesible a inspectores.
    """
    usuario_id = request.session.get("usuario_id")
    usuario = get_object_or_404(Usuario, id=usuario_id)
    if not usuario.es_inspector:
        return redirect("inicio")
    return render(request, 'inspectores/resumen_cobros.html')

@require_role("inspector", "admin")
def resumen_infracciones(request):
    """
    Vista de resumen de infracciones registradas por inspectores.
    - Solo accesible a inspectores.
    """
    usuario_id = request.session.get("usuario_id")
    usuario = get_object_or_404(Usuario, id=usuario_id)
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
    usuario_id = request.session.get("usuario_id")
    usuario = get_object_or_404(Usuario, id=usuario_id)
    if not usuario.es_vendedor:
        return redirect("inicio")
    return render(request, 'vendedores/panel.html', {"vendedor": usuario})


@require_role("vendedor", "admin")
def resumen_caja(request):
    usuario_id = request.session.get("usuario_id")
    usuario = get_object_or_404(Usuario, id=usuario_id)

    registros = Estacionamiento.objects.filter(registrado_por=usuario).order_by("-hora_inicio")

    return render(request, 'vendedores/resumen_caja.html', {"registros": registros})

# =========================================================
# VIEWS LOGIN / LOGOUT

class UsuarioLoginView(LoginView):
    template_name = "usuarios/login.html"
    redirect_authenticated_user = True

def logout_view(request):
    """
    - Cierra sesión del usuario.
    - Redirige al login.
    """
    request.session.flush()
    return render(request, "usuarios/login.html", {"error": "Debe iniciar sesión"})
