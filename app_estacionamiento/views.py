#ESTACIONAMIENTO_APP/app_estacionamiento/views.py
# Archivo: views.py - Vistas principales del sitio

from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from .models import Usuario, Vehiculo, Subcuadra, Estacionamiento, Infraccion
from .estrategias import EstrategiaExencion
from .factories import EstacionamientoFactory


def registrar_infraccion(request):
    """
    Vista para que el inspector registre una infracción.
    Verifica si el vehículo está exento o pagado.
    # aplica Strategy y lógica de negocio
    """
    if request.method == 'POST':
        inspector_id = request.POST['inspector_id']
        patente = request.POST['patente']
        subcuadra_id = request.POST['subcuadra_id']

        inspector = get_object_or_404(Usuario, id=inspector_id, es_inspector=True)
        vehiculo = get_object_or_404(Vehiculo, patente=patente)
        subcuadra = get_object_or_404(Subcuadra, id=subcuadra_id)

        if vehiculo.esta_exento_en(subcuadra):
            return render(request, 'registrar_infraccion.html', {
                'mensaje': 'El vehículo está exento en esta subcuadra.',
                'subcuadras': Subcuadra.objects.all(),
                'inspectores': Usuario.objects.filter(es_inspector=True)
            })

        estacionamiento = Estacionamiento.objects.filter(vehiculo=vehiculo, subcuadra=subcuadra, activo=True).first()
        if not estacionamiento:
            infraccion = Infraccion.objects.create(
                vehiculo=vehiculo,
                inspector=inspector,
                subcuadra=subcuadra,
                fecha=timezone.now()
            )
            return render(request, 'registrar_infraccion.html', {
                'mensaje': 'Infracción registrada. Se notificará si no se paga en 15 minutos.',
                'subcuadras': Subcuadra.objects.all(),
                'inspectores': Usuario.objects.filter(es_inspector=True)
            })

        infraccion = Infraccion.objects.create(
            vehiculo=vehiculo,
            inspector=inspector,
            subcuadra=subcuadra,
            estacionamiento=estacionamiento,
            fecha=timezone.now()
        )
        resultado = infraccion.verificar_cancelacion()
        return render(request, 'registrar_infraccion.html', {
            'mensaje': resultado,
            'subcuadras': Subcuadra.objects.all(),
            'inspectores': Usuario.objects.filter(es_inspector=True)
        })

    return render(request, 'registrar_infraccion.html', {
        'subcuadras': Subcuadra.objects.all(),
        'inspectores': Usuario.objects.filter(es_inspector=True)
    })

def estacionar_auto(request):
    """
    Vista para que un usuario estacione un vehículo en una subcuadra.
    Valida que no haya otro estacionamiento activo.
    # aplica Factory y validación
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
            return render(request, 'estacionar_auto.html', {
                'error': 'Datos inválidos. Verificá correo, patente y subcuadra.',
                'subcuadras': Subcuadra.objects.all()
            })

        # Validación: evitar duplicado
        if Estacionamiento.objects.filter(vehiculo=vehiculo, activo=True).exists():
            return render(request, 'estacionar_auto.html', {
                'error': 'Este vehículo ya tiene un estacionamiento activo.',
                'subcuadras': Subcuadra.objects.all()
            })

        # Crear estacionamiento
        EstacionamientoFactory.crear(vehiculo, subcuadra)
        return redirect('home')

    return render(request, 'estacionar_auto.html', {
        'subcuadras': Subcuadra.objects.all()
    })

def finalizar_estacionamiento(request, estacionamiento_id):
    """
    Vista para finalizar un estacionamiento.
    Valida que el usuario tenga saldo suficiente.
    # aplica Strategy y validación
    """
    estacionamiento = get_object_or_404(Estacionamiento, id=estacionamiento_id)

    if not estacionamiento.activo:
        return render(request, 'finalizar_estacionamiento.html', {
            'error': 'Este estacionamiento ya fue finalizado.',
            'estacionamiento': estacionamiento
        })

    estrategia = EstrategiaExencion()
    duracion = (timezone.now() - estacionamiento.hora_inicio).total_seconds() / 3600
    costo_estimado = estrategia.calcular(estacionamiento.vehiculo, estacionamiento.subcuadra, duracion)

    usuario = estacionamiento.vehiculo.usuarios.first()
    if usuario.saldo < costo_estimado:
        return render(request, 'finalizar_estacionamiento.html', {
            'error': 'Saldo insuficiente para finalizar el estacionamiento.',
            'estacionamiento': estacionamiento,
            'costo_estimado': round(costo_estimado, 2)
        })

    # Finalizar y descontar saldo
    estacionamiento.finalizar(estrategia)
    usuario.saldo -= estacionamiento.costo
    usuario.save()

    return render(request, 'finalizar_estacionamiento.html', {
        'mensaje': f'Estacionamiento finalizado. Costo: ${estacionamiento.costo}',
        'estacionamiento': estacionamiento
    })

def home(request):
    """
    Vista principal del sistema.
    Muestra opciones de navegación.
    """
    return render(request, 'home.html')
