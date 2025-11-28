# ESTACIONAMIENTO_APP/app_estacionamiento/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from .models import Usuario, Vehiculo, Subcuadra, Estacionamiento, Infraccion
from .estrategias import EstrategiaExencion
from .factories import EstacionamientoFactory
from decimal import Decimal, ROUND_HALF_UP
from .decorators import require_role, require_login

# =========================================================
# HOME GENERAL
# =========================================================
def home(request):
    """
    Vista principal del sistema.
    - Si hay usuario logueado, redirige al inicio de usuarios.
    - Si no hay sesión, redirige al login.
    """
    if not request.session.get("usuario_id"):
        return redirect("login")
    return redirect("inicio_usuarios")

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

# =========================================================
# VIEWS USUARIOS
# =========================================================
@require_role("conductor")
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

def usuarios_historial(request):
    usuario_id = request.session.get("usuario_id")
    usuario = get_object_or_404(Usuario, id=usuario_id)
    estacionamientos = Estacionamiento.objects.filter(registrado_por=usuario).order_by("-hora_inicio")
    return render(request, "usuarios/historial_estacionamientos.html", {
        "usuario": usuario,
        "estacionamientos": estacionamientos
    })

@require_role("conductor", "inspector", "admin")
def inicio_usuarios(request):
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return redirect("login")
    usuario = get_object_or_404(Usuario, id=usuario_id)

    estacionamientos_activos = Estacionamiento.objects.filter(
        vehiculo__usuarios=usuario,
        activo=True
    )

    return render(request, "usuarios/inicio_usuarios.html", {
        "usuario": usuario,
        "estacionamientos": estacionamientos_activos,
    })

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
        return redirect("login")

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
        if vehiculo.exento_en_zona or vehiculo.subcuadras_exentas.exists():
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

def finalizar_estacionamiento(request, estacionamiento_id):
    usuario_id = request.session.get("usuario_id")
    usuario = get_object_or_404(Usuario, id=usuario_id)
    estacionamiento = get_object_or_404(Estacionamiento, id=estacionamiento_id)

    if not estacionamiento.activo:
        return redirect("usuarios_historial")

    costo_final = estacionamiento.finalizar()

    if usuario.saldo < costo_final:
        # revertir correctamente
        estacionamiento.activo = True
        estacionamiento.hora_fin = None
        estacionamiento.costo = Decimal("0.00")
        estacionamiento.save()
        return redirect("usuarios_historial")

    usuario.saldo -= costo_final
    usuario.save()
    return redirect("usuarios_historial")


def historial_estacionamientos(request):
    """
    Muestra historial de estacionamientos del usuario logueado.
    """
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return redirect("login")
    usuario = get_object_or_404(Usuario, id=usuario_id)

    estacionamientos = Estacionamiento.objects.filter(vehiculo__usuarios=usuario)

    return render(request, 'usuarios/historial_estacionamientos.html', {
        'estacionamientos': estacionamientos
    })

def historial_infracciones(request):
    """
    Muestra historial de infracciones del usuario logueado.
    """
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return redirect("login")
    usuario = get_object_or_404(Usuario, id=usuario_id)

    infracciones = Infraccion.objects.filter(vehiculo__usuarios=usuario)

    return render(request, 'usuarios/historial_infracciones.html', {
        'infracciones': infracciones
    })

def usuarios_infracciones(request):
    usuario_id = request.session.get("usuario_id")
    usuario = get_object_or_404(Usuario, id=usuario_id)
    infracciones = Infraccion.objects.filter(vehiculo__usuarios=usuario).order_by("-fecha")
    return render(request, "usuarios/historial_infracciones.html", {
        "usuario": usuario,
        "infracciones": infracciones
    })

@require_login
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

def verificar_vehiculo(request):
    """
    Inspector verifica un vehículo solo ingresando la patente.
    - Si exento global → Verificado exento en toda la zona.
    - Si exento en subcuadras → se listan esas subcuadras.
    - Si tiene estacionamiento activo → Pagado.
    - Si no → No registrado.
    """
    usuario_id = request.session.get("usuario_id")
    inspector = get_object_or_404(Usuario, id=usuario_id)

    if not inspector.es_inspector and not inspector.es_admin:
        return redirect("inicio")

    resultado = None

    if request.method == "POST":
        patente = request.POST.get("patente")

        try:
            vehiculo = Vehiculo.objects.get(patente=patente)

            estado = "No registrado"
            detalle = None
            exento = False

            # Exención global
            if vehiculo.exento_en_zona:
                estado = "Exento"
                exento = True
                detalle = "Verificado exento en toda la zona"

            # Exenciones específicas
            elif vehiculo.subcuadras_exentas.exists():
                estado = "Exento"
                exento = True
                detalle = "Verificado exento en subcuadras: " + ", ".join(
                    str(s) for s in vehiculo.subcuadras_exentas.all()
                )

            # Estacionamiento activo
            else:
                estacionamiento_activo = Estacionamiento.objects.filter(
                    vehiculo=vehiculo, activo=True
                ).first()
                if estacionamiento_activo:
                    estado = "Pagado"
                    detalle = f"Estacionamiento activo desde {estacionamiento_activo.hora_inicio}"

            resultado = {
                "patente": vehiculo.patente,
                "estado": estado,
                "detalle": detalle,
                "exento": exento,
            }

        except Vehiculo.DoesNotExist:
            resultado = {
                "patente": patente,
                "estado": "No registrado",
            }

    return render(request, "inspectores/verificar_vehiculo.html", {
        "resultado": resultado
    })

@require_role("inspector", "admin")
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

@require_role("vendedor", "admin")
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

        if vehiculo.exento_en_zona or vehiculo.subcuadras_exentas.exists():
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
# =========================================================
def login_view(request):
    """
    Vista de login simple.
    - Usa correo y contraseña del modelo Usuario.
    - Si son correctos, guarda usuario_id en sesión.
    - Redirige al inicio general.
    """
    if request.method == "POST":
        correo = request.POST.get("correo")
        password = request.POST.get("password")

        try:
            usuario = Usuario.objects.get(correo=correo, password=password)
            request.session["usuario_id"] = usuario.id
            return redirect("inicio")
        except Usuario.DoesNotExist:
            return render(request, "login.html", {"error": "Correo o contraseña incorrectos"})

    return render(request, "login.html")


def logout_view(request):
    """
    - Cierra sesión del usuario.
    - Redirige al login.
    """
    request.session.flush()
    return redirect("login")
