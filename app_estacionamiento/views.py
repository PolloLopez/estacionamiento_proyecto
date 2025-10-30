#app_estacionamiento/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from .models import Usuario, Vehiculo, Subcuadra, Estacionamiento, Infraccion
from .estrategias import EstrategiaExencion

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
