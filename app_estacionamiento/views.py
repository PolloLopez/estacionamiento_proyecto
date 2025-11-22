# ESTACIONAMIENTO_APP/app_estacionamiento/views.py
# Archivo: views.py
# Vistas del sistema organizadas por rol, con login/logout y chequeos de sesión.

from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from .models import Usuario, Vehiculo, Subcuadra, Estacionamiento, Infraccion
from .estrategias import EstrategiaExencion
from .factories import EstacionamientoFactory
from decimal import Decimal, ROUND_HALF_UP

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


# =========================================================
# VIEWS USUARIOS
# =========================================================
def inicio_usuarios(request):
    """
    Pantalla inicial para usuarios.
    - Muestra nombre del usuario logueado.
    - Lista estacionamientos activos asociados a sus vehículos.
    """
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
    Vista para registrar un nuevo estacionamiento.
    - Valida usuario, vehículo y subcuadra.
    - Verifica que el vehículo no tenga estacionamiento activo.
    - Valida duración en pasos de 0.5 horas.
    - Usa EstacionamientoFactory para crear el registro.
    """
    if request.method == 'POST':
        correo = request.POST.get('correo')
        patente = request.POST.get('patente')
        subcuadra_id = request.POST.get('subcuadra_id')
        duracion = request.POST.get('duracion')

        try:
            usuario = Usuario.objects.get(correo=correo)
            vehiculo = Vehiculo.objects.get(patente=patente)
            subcuadra = Subcuadra.objects.get(id=subcuadra_id)
        except (Usuario.DoesNotExist, Vehiculo.DoesNotExist, Subcuadra.DoesNotExist):
            return render(request, 'usuarios/estacionar_vehiculo.html', {
                'error': 'Datos inválidos. Verificá correo, patente y subcuadra.',
                'subcuadras': Subcuadra.objects.all()
            })

        # Validar que no tenga estacionamiento activo
        if Estacionamiento.objects.filter(vehiculo=vehiculo, activo=True).exists():
            return render(request, 'usuarios/estacionar_vehiculo.html', {
                'error': 'El vehículo ya tiene un estacionamiento activo.',
                'subcuadras': Subcuadra.objects.all()
            })

        # Validar duración en pasos de 0.5 horas
        try:
            duracion = Decimal(duracion)
            if duracion <= 0 or (duracion * 2) % 1 != 0:
                raise ValueError("Duración inválida")
        except Exception:
            return render(request, 'usuarios/estacionar_vehiculo.html', {
                'error': 'La duración debe ser en pasos de 0.5 horas (ej: 0.5, 1, 1.5, 2).',
                'subcuadras': Subcuadra.objects.all()
            })

        # Crear estacionamiento con Factory
        EstacionamientoFactory.crear(vehiculo, subcuadra, duracion)
        return redirect('inicio_usuarios')

    return render(request, 'usuarios/estacionar_vehiculo.html', {
        'subcuadras': Subcuadra.objects.all()
    })


def finalizar_estacionamiento(request, estacionamiento_id):
    """
    Finaliza un estacionamiento activo.
    - Busca el estacionamiento por ID.
    - Calcula costo usando EstrategiaExencion.
    - Valida que el usuario tenga saldo suficiente.
    - Descuenta saldo y guarda cambios.
    """
    estacionamiento = get_object_or_404(Estacionamiento, id=estacionamiento_id)

    if not estacionamiento.activo:
        return render(request, 'usuarios/finalizar_estacionamiento.html', {
            'error': 'Este estacionamiento ya está finalizado.',
            'estacionamiento': estacionamiento
        })

    estrategia = EstrategiaExencion()
    duracion = (timezone.now() - estacionamiento.hora_inicio).total_seconds() / 3600

    costo_estimado = estrategia.calcular(
        estacionamiento.vehiculo, estacionamiento.subcuadra, duracion
    )

    costo_estimado_decimal = Decimal(str(costo_estimado)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    usuario = estacionamiento.vehiculo.usuarios.first()
    if usuario.saldo < costo_estimado_decimal:
        return render(request, 'usuarios/finalizar_estacionamiento.html', {
            'error': 'Saldo insuficiente para finalizar.',
            'estacionamiento': estacionamiento,
            'costo_estimado': costo_estimado_decimal
        })

    estacionamiento.finalizar(estrategia)
    usuario.saldo -= estacionamiento.costo
    usuario.save()

    return render(request, 'usuarios/finalizar_estacionamiento.html', {
        'mensaje': f'Estacionamiento finalizado. Costo: ${estacionamiento.costo}',
        'estacionamiento': estacionamiento
    })


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


def cargar_saldo(request):
    """
    Vista para cargar saldo en la cuenta del usuario.
    """
    return render(request, 'usuarios/cargar_saldo.html')


def consultar_deuda(request):
    """
    Vista para consultar deuda del usuario.
    """
    return render(request, 'usuarios/consultar_deuda.html')


# =========================================================
# VIEWS INSPECTORES
# =========================================================
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
    Vista para verificar estado de un vehículo.
    - Solo accesible a inspectores.
    """
    usuario_id = request.session.get("usuario_id")
    usuario = get_object_or_404(Usuario, id=usuario_id)
    if not usuario.es_inspector:
        return redirect("inicio")
    return render(request, 'inspectores/verificar_vehiculo.html')


def registrar_estacionamiento_manual(request):
    """
    Vista para registrar estacionamiento manualmente (por inspector).
    """
    usuario_id = request.session.get("usuario_id")
    usuario = get_object_or_404(Usuario, id=usuario_id)
    if not usuario.es_inspector:
        return redirect("inicio")
    return render(request, 'inspectores/registrar_estacionamiento_manual.html')


def registrar_infraccion(request):
    """
    Registro de infracción por inspector.
    - Valida inspector.
    - Verifica si el vehículo está exento.
    - Si tiene estacionamiento activo, lo asocia.
    - Si no, crea infracción independiente.
    """
    usuario_id = request.session.get("usuario_id")
    inspector = get_object_or_404(Usuario, id=usuario_id, es_inspector=True)

    if request.method == 'POST':
        patente = request.POST['patente']
        subcuadra_id = request.POST['subcuadra_id']

        vehiculo = get_object_or_404(Vehiculo, patente=patente)
        subcuadra = get_object_or_404(Subcuadra, id=subcuadra_id)

        if vehiculo.esta_exento_en(subcuadra):
            mensaje = "El vehículo está exento."
        else:
            estacionamiento = Estacionamiento.objects.filter(
                vehiculo=vehiculo, subcuadra=subcuadra, activo=True
            ).first()

            if estacionamiento:
                infraccion = Infraccion.objects.create(
                    vehiculo=vehiculo,
                    inspector=inspector,
                    subcuadra=subcuadra,
                    estacionamiento=estacionamiento,
                    fecha=timezone.now()
                )
                mensaje = infraccion.verificar_cancelacion()
            else:
                Infraccion.objects.create(
                    vehiculo=vehiculo,
                    inspector=inspector,
                    subcuadra=subcuadra,
                    fecha=timezone.now()
                )
                mensaje = "Infracción registrada."

        return render(request, 'inspectores/registrar_infraccion.html', {
            'mensaje': mensaje,
            'subcuadras': Subcuadra.objects.all()
        })

    return render(request, 'inspectores/registrar_infraccion.html', {
        'subcuadras': Subcuadra.objects.all()
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
def panel_vendedores(request):
    """
    Panel principal de vendedores.
    - Solo accesible a vendedores.
    """
    usuario_id = request.session.get("usuario_id")
    usuario = get_object_or_404(Usuario, id=usuario_id)
    if not usuario.es_vendedor:
        return redirect("inicio")
    return render(request, 'vendedores/panel.html')


def registrar_estacionamiento_vendedor(request):
    """
    Vista para que un vendedor registre un estacionamiento.
    - Solo accesible a vendedores.
    """
    usuario_id = request.session.get("usuario_id")
    usuario = get_object_or_404(Usuario, id=usuario_id)
    if not usuario.es_vendedor:
        return redirect("inicio")
    return render(request, 'vendedores/registrar_estacionamiento.html')


def resumen_caja(request):
    """
    Vista de resumen de caja de vendedores.
    - Solo accesible a vendedores.
    """
    usuario_id = request.session.get("usuario_id")
    usuario = get_object_or_404(Usuario, id=usuario_id)
    if not usuario.es_vendedor:
        return redirect("inicio")
    return render(request, 'vendedores/resumen_caja.html')


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
    Vista de logout simple.
    - Borra la sesión actual.
    - Redirige al login.
    """
    request.session.flush()
    return redirect("login")
