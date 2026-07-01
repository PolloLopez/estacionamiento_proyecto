# app_estacionamiento/services_verificacion.py

from django.urls import reverse
from django.utils import timezone
from datetime import timedelta, date

from app_estacionamiento.models import (
    Vehiculo, Estacionamiento, Estado,
    VerificacionInspector, AbonoMensual
)
from app_estacionamiento.domain.verificacion import ResultadoVerificacion
from app_estacionamiento.domain.enums import EstadoVehiculo


def _url_infraccion(patente):
    return reverse("inspectores_registrar_infraccion") + f"?patente={patente}"


def _tolerancia_inspector(municipio):
    """
    Devuelve la tolerancia en minutos para la ventana entre verificaciones del inspector.
    Esta tolerancia es fija (15 min); es distinta de la tolerancia de pago de multa
    que vive en municipio.tolerancia_multa_minutos.
    """
    return 15


def verificar_estado_vehiculo(patente, usuario, subcuadra):
    """
    Verifica el estado de un vehiculo para el inspector.

    Orden de evaluacion:
    1. Vehiculo no registrado   -> NO_REGISTRADO
    2. Exento total             -> EXENTO_TOTAL
    3. Estacionamiento activo   -> PAGADO
    4. Abono mensual vigente    -> ABONO_ACTIVO
    5. Exento parcial           -> EXENTO_PARCIAL
    6. Dentro de tolerancia     -> PENDIENTE_PAGO
    7. Sin pago                 -> IMPAGO
    """
    municipio = getattr(usuario, "municipio", None)

    vehiculo = Vehiculo.objects.filter(patente=patente).first()

    if not vehiculo:
        return ResultadoVerificacion(
            patente=patente,
            estado=EstadoVehiculo.NO_REGISTRADO,
            estacionamiento_activo=False,
            subcuadras_exentas=[],
            registrar_infraccion_url=_url_infraccion(patente)
        )

    # Guardar la verificacion anterior ANTES de crear la nueva
    verificacion_anterior = VerificacionInspector.objects.filter(
        vehiculo=vehiculo
    ).order_by("-fecha").first()

    # Registrar esta verificacion
    VerificacionInspector.objects.create(
        vehiculo=vehiculo,
        inspector=usuario,
        subcuadra=subcuadra,
        resultado="verificado"
    )

    # 1. EXENTO TOTAL
    if getattr(vehiculo, "exento_global", False):
        return ResultadoVerificacion(
            patente=patente,
            estado=EstadoVehiculo.EXENTO_TOTAL,
            estacionamiento_activo=True
        )

    # 2. ESTACIONAMIENTO ACTIVO
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

    # 3. ABONO MENSUAL VIGENTE
    if municipio:
        hoy = date.today()
        mes_actual = hoy.replace(day=1)
        abono_activo = AbonoMensual.objects.filter(
            vehiculo=vehiculo,
            municipio=municipio,
            mes=mes_actual,
        ).exists()

        if abono_activo:
            return ResultadoVerificacion(
                patente=patente,
                estado=EstadoVehiculo.ABONO_ACTIVO,
                estacionamiento_activo=True
            )

    # 4. EXENTO PARCIAL
    if hasattr(vehiculo, "subcuadras_exentas") and vehiculo.subcuadras_exentas.exists():
        subcuadras_del_vehiculo = list(vehiculo.subcuadras_exentas.all())
        if subcuadra and vehiculo.subcuadras_exentas.filter(id=subcuadra.id).exists():
            return ResultadoVerificacion(
                patente=patente,
                estado=EstadoVehiculo.EXENTO_PARCIAL,
                subcuadras_exentas=subcuadras_del_vehiculo,
                estacionamiento_activo=False,
                exento_en_subcuadra_actual=True
            )

    # 5. TOLERANCIA del inspector (entre verificaciones sucesivas)
    tolerancia_minutos = _tolerancia_inspector(municipio)
    if verificacion_anterior:
        tiempo_desde_ultima = timezone.now() - verificacion_anterior.fecha
        if tiempo_desde_ultima <= timedelta(minutes=tolerancia_minutos):
            return ResultadoVerificacion(
                patente=patente,
                estado=EstadoVehiculo.PENDIENTE_PAGO,
                subcuadras_exentas=[],
                estacionamiento_activo=False
            )

    # 6. IMPAGO
    return ResultadoVerificacion(
        patente=patente,
        estado=EstadoVehiculo.IMPAGO,
        estacionamiento_activo=False,
        registrar_infraccion_url=_url_infraccion(patente)
    )
