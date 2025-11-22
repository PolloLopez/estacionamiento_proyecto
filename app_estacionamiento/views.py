#ESTACIONAMIENTO_APP/app_estacionamiento/views.py
# Archivo: views.py
# Vistas del sistema organizadas por rol.

from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from .models import Usuario, Vehiculo, Subcuadra, Estacionamiento, Infraccion
from .estrategias import EstrategiaExencion
from .factories import EstacionamientoFactory


# =========================================================
# HOME GENERAL
# =========================================================
def home(request):
    """
    Redirige al inicio de usuarios.
    Se usa como home principal del sitio.
    """
    return redirect('inicio_usuarios')


# =========================================================
# VIEWS USUARIOS
# =========================================================
def inicio_usuarios(request):
    """
    Pantalla principal del usuario.
    Muestra menú de acciones disponibles.
    """
    return render(request, 'usuarios/inicio_usuarios.html')


def estacionar_vehiculo(request):
    """
    Vista para que un usuario estacione su vehículo.
    - Valida usuario, vehículo y subcuadra.
    - Verifica que no tenga un estacionamiento activo.
    - Usa EstacionamientoFactory para crear el registro.
    """
    if request.method == 'POST':
        correo = request.POST['correo']
        patente = request.POST['patente']
        subcuadra_id = request.POST['subcuadra_id']

        try:
            usuario = Usuario.objects.get(correo=correo)
            vehiculo = Vehiculo.objects.get(patente=patente)
            subcuadra = Subcuadra.objects.get(id=subcuadra_id)
        except (Usuario.DoesNotExist, Vehiculo.DoesNotExist, Subcuadra.DoesNotExist):
            return render(request, 'usuarios/estacionar_vehiculo.html', {
                'error': 'Datos inválidos. Verificá correo, patente y subcuadra.',
                'subcuadras': Subcuadra.objects.all()
            })

        if Estacionamiento.objects.filter(vehiculo=vehiculo, activo=True).exists():
            return render(request, 'usuarios/estacionar_vehiculo.html', {
                'error': 'El vehículo ya tiene un estacionamiento activo.',
                'subcuadras': Subcuadra.objects.all()
            })

        EstacionamientoFactory.crear(vehiculo, subcuadra)
        return redirect('inicio_usuarios')

    return render(request, 'usuarios/estacionar_vehiculo.html', {
        'subcuadras': Subcuadra.objects.all()
    })


def finalizar_estacionamiento(request, estacionamiento_id):
    """
    Finaliza un estacionamiento:
    - Calcula costo según estrategia de exención.
    - Valida saldo del usuario.
    - Descuenta y guarda.
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

    usuario = estacionamiento.vehiculo.usuarios.first()
    if usuario.saldo < costo_estimado:
        return render(request, 'usuarios/finalizar_estacionamiento.html', {
            'error': 'Saldo insuficiente para finalizar.',
            'estacionamiento': estacionamiento,
            'costo_estimado': round(costo_estimado, 2)
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
    Muestra historial de estacionamientos del usuario.
    """
    return render(request, 'usuarios/historial_estacionamientos.html')


def historial_infracciones(request):
    """
    Muestra infracciones del usuario.
    """
    return render(request, 'usuarios/historial_infracciones.html')


def cargar_saldo(request):
    return render(request, 'usuarios/cargar_saldo.html')


def consultar_deuda(request):
    return render(request, 'usuarios/consultar_deuda.html')


# =========================================================
# VIEWS INSPECTORES
# =========================================================
def panel_inspectores(request):
    return render(request, 'inspectores/panel.html')


def verificar_vehiculo(request):
    return render(request, 'inspectores/verificar_vehiculo.html')


def registrar_estacionamiento_manual(request):
    return render(request, 'inspectores/registrar_estacionamiento_manual.html')


def registrar_infraccion(request):
    """
    Registro de infracción:
    - Valida inspector
    - Verifica si el vehículo está exento
    - Verifica estacionamiento activo
    - Crea infracción
    """
    if request.method == 'POST':
        inspector_id = request.POST['inspector_id']
        patente = request.POST['patente']
        subcuadra_id = request.POST['subcuadra_id']

        inspector = get_object_or_404(Usuario, id=inspector_id, es_inspector=True)
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
            'inspectores': Usuario.objects.filter(es_inspector=True),
            'subcuadras': Subcuadra.objects.all()
        })

    return render(request, 'inspectores/registrar_infraccion.html', {
        'inspectores': Usuario.objects.filter(es_inspector=True),
        'subcuadras': Subcuadra.objects.all()
    })


def resumen_cobros(request):
    return render(request, 'inspectores/resumen_cobros.html')


def resumen_infracciones(request):
    return render(request, 'inspectores/resumen_infracciones.html')


# =========================================================
# VIEWS VENDEDORES
# =========================================================
def panel_vendedores(request):
    return render(request, 'vendedores/panel.html')


def registrar_estacionamiento_vendedor(request):
    return render(request, 'vendedores/registrar_estacionamiento.html')


def resumen_caja(request):
    return render(request, 'vendedores/resumen_caja.html')


# =========================================================
# VIEWS ADMINISTRADOR DEL SISTEMA
# =========================================================
def inicio_admin(request):
    return render(request, 'admin/inicio_admin.html')


def gestionar_usuarios(request):
    return render(request, 'admin/gestionar_usuarios.html')


def gestionar_inspectores(request):
    return render(request, 'admin/gestionar_inspectores.html')


def gestionar_vendedores(request):
    return render(request, 'admin/gestionar_vendedores.html')


def gestionar_tarifas(request):
    return render(request, 'admin/gestionar_tarifas.html')


def gestionar_horarios(request):
    return render(request, 'admin/gestionar_horarios.html')


def gestionar_infracciones(request):
    return render(request, 'admin/gestionar_infracciones.html')
