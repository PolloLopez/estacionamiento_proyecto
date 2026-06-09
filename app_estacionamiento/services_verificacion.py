# app_estacionamiento/services_verificacion.py

from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from app_estacionamiento.models import (
    Vehiculo, Estacionamiento, Estado,
    VerificacionInspector
)
from app_estacionamiento.domain.verificacion import ResultadoVerificacion
from app_estacionamiento.domain.enums import EstadoVehiculo


def _url_infraccion(patente):
    return reverse("inspectores_registrar_infraccion") + f"?patente={patente}"


def obtener_tolerancia():
    # TODO: después lo leemos desde configuración del admin
    return 15


def verificar_estado_vehiculo(patente, usuario, subcuadra):

    vehiculo = Vehiculo.objects.filter(patente=patente).first()

    if not vehiculo:
        return ResultadoVerificacion(
            patente=patente,
            estado=EstadoVehiculo.NO_REGISTRADO,
            estacionamiento_activo=False,
            subcuadras_exentas=[...],
            registrar_infraccion_url=_url_infraccion(patente)
        )

    # Guardar la verificación anterior ANTES de crear la nueva
    # (para calcular tolerancia correctamente)
    verificacion_anterior = VerificacionInspector.objects.filter(
        vehiculo=vehiculo
    ).order_by("-fecha").first()

    # Registrar esta verificación
    VerificacionInspector.objects.create(
        vehiculo=vehiculo,
        inspector=usuario,
        subcuadra=subcuadra,
        resultado="verificado"
    )

    # EXENTO TOTAL
    if getattr(vehiculo, "exento_global", False):
        return ResultadoVerificacion(
            patente=patente,
            estado=EstadoVehiculo.EXENTO_TOTAL,
            estacionamiento_activo=True
        )

    # ESTACIONAMIENTO ACTIVO
    estacionamiento = Estacionamiento.objects.filter(
        vehiculo=vehiculo,
        estado=Estado.ACTIVO
    ).order_by("-hora_inicio").first()

    if estacionamiento:
        return ResultadoVerificacion(
            patente=patente,
            estado=EstadoVehiculo.PAGADO,
            estacionamiento_activo=True
        )

    # EXENTO PARCIAL
    if hasattr(vehiculo, "subcuadras_exentas") and vehiculo.subcuadras_exentas.exists():
        subcuadras_del_vehiculo = list(vehiculo.subcuadras_exentas.all())
        # Si la subcuadra actual está entre las exentas → OK, no infraccionar
        if subcuadra and vehiculo.subcuadras_exentas.filter(id=subcuadra.id).exists():
            return ResultadoVerificacion(
                patente=patente,
                estado=EstadoVehiculo.EXENTO_PARCIAL,
                subcuadras_exentas=subcuadras_del_vehiculo,
                estacionamiento_activo=False,
                exento_en_subcuadra_actual=True
            )
        # La subcuadra actual NO está exenta → sí debe pagar (sigue flujo normal)

    # TOLERANCIA: usar la verificación anterior al inspector actual
    tolerancia_minutos = obtener_tolerancia()
    if verificacion_anterior:
        tiempo_desde_ultima = timezone.now() - verificacion_anterior.fecha
        if tiempo_desde_ultima <= timedelta(minutes=tolerancia_minutos):
            return ResultadoVerificacion(
                patente=patente,
                estado=EstadoVehiculo.PENDIENTE_PAGO,
                subcuadras_exentas=[],
                estacionamiento_activo=False
            )

    # IMPAGO
    return ResultadoVerificacion(
        patente=patente,
        estado=EstadoVehiculo.IMPAGO,
        estacionamiento_activo=False,
        registrar_infraccion_url=_url_infraccion(patente)
    )