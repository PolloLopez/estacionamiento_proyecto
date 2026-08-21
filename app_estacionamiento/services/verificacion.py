# app_estacionamiento/services/verificacion.py
"""
Lógica de negocio para verificar el estado de un vehículo en la vía pública.

Responsabilidades:
- Determinar si un vehículo está pagado, en deuda, exento o con abono activo
- Registrar la verificación del inspector (trazabilidad)
- Calcular tolerancia entre verificaciones consecutivas
"""

from datetime import date, timedelta

from django.urls import reverse
from django.utils import timezone

from app_estacionamiento.domain.enums import EstadoVehiculo
from app_estacionamiento.domain.verificacion import ResultadoVerificacion
from app_estacionamiento.domain.enums import MINUTOS_ENTRE_INFRACCIONES
from app_estacionamiento.models import (
    AbonoMensual,
    Estado,
    Estacionamiento,
    Infraccion,
    VerificacionInspector,
    Vehiculo,
)

# Minutos de tolerancia entre verificaciones sucesivas del inspector.
# Distinto de municipio.tolerancia_multa_minutos (que es la ventana de pago de multas).
_TOLERANCIA_INSPECTOR_MINUTOS = 15


def _url_infraccion(patente):
    """URL de alta de infracción pre-cargada con la patente."""
    return reverse("inspectores_registrar_infraccion") + f"?patente={patente}"


def verificar_estado_vehiculo(patente, usuario, subcuadra):
    """
    Verifica el estado de un vehículo para el inspector.

    Orden de evaluación:
    1. Vehículo no registrado       → NO_REGISTRADO
    2. Exento total                 → EXENTO_TOTAL
    3. Estacionamiento activo       → PAGADO
    4. Abono mensual vigente        → ABONO_ACTIVO
    5. Exento parcial en subcuadra  → EXENTO_PARCIAL
    6. Dentro de tolerancia         → PENDIENTE_PAGO
    7. Infracción reciente (<15min) → INFRACCION_RECIENTE
    8. Sin pago                     → IMPAGO

    Registra siempre la verificación para trazabilidad.
    """
    municipio = getattr(usuario, "municipio", None)

    vehiculo = Vehiculo.objects.filter(patente=patente).first()

    if not vehiculo:
        return ResultadoVerificacion(
            patente=patente,
            estado=EstadoVehiculo.NO_REGISTRADO,
            estacionamiento_activo=False,
            subcuadras_exentas=[],
            registrar_infraccion_url=_url_infraccion(patente),
        )

    # Guardar la verificación anterior ANTES de crear la nueva (para tolerancia)
    verificacion_anterior = VerificacionInspector.objects.filter(
        vehiculo=vehiculo
    ).order_by("-fecha").first()

    VerificacionInspector.objects.create(
        vehiculo=vehiculo,
        inspector=usuario,
        subcuadra=subcuadra,
        resultado="verificado",
    )

    # 1. EXENTO TOTAL — solo si la vigencia no expiró
    # vigencia_exencion=None significa sin vencimiento (indefinida).
    # Si la fecha venció, el vehículo cae al flujo normal y puede recibir infracción.
    if getattr(vehiculo, "exento_global", False):
        vigencia = getattr(vehiculo, "vigencia_exencion", None)
        if vigencia is None or vigencia >= date.today():
            return ResultadoVerificacion(
                patente=patente,
                estado=EstadoVehiculo.EXENTO_TOTAL,
                estacionamiento_activo=True,
                tipo_exencion=getattr(vehiculo, "tipo_exencion", None),
            )

    # 2. ESTACIONAMIENTO ACTIVO
    estacionamiento = Estacionamiento.objects.filter(
        vehiculo=vehiculo, estado=Estado.ACTIVO
    ).order_by("-hora_inicio").first()

    if estacionamiento:
        return ResultadoVerificacion(
            patente=patente,
            estado=EstadoVehiculo.PAGADO,
            estacionamiento_activo=True,
        )

    # 3. ABONO MENSUAL VIGENTE
    if municipio:
        hoy       = date.today()
        mes_actual = hoy.replace(day=1)
        if AbonoMensual.objects.filter(
            vehiculo=vehiculo, municipio=municipio, mes=mes_actual
        ).exists():
            return ResultadoVerificacion(
                patente=patente,
                estado=EstadoVehiculo.ABONO_ACTIVO,
                estacionamiento_activo=True,
            )

    # 4. EXENTO PARCIAL — solo si la vigencia no expiró
    vigencia_parcial = getattr(vehiculo, "vigencia_exencion", None)
    exencion_parcial_activa = (vigencia_parcial is None or vigencia_parcial >= date.today())
    if exencion_parcial_activa and hasattr(vehiculo, "subcuadras_exentas") and vehiculo.subcuadras_exentas.exists():
        subcuadras_del_vehiculo = list(vehiculo.subcuadras_exentas.all())
        if subcuadra and vehiculo.subcuadras_exentas.filter(id=subcuadra.id).exists():
            # El vehiculo esta en su zona exenta -> libre, no infraccionar
            return ResultadoVerificacion(
                patente=patente,
                estado=EstadoVehiculo.EXENTO_PARCIAL,
                subcuadras_exentas=subcuadras_del_vehiculo,
                estacionamiento_activo=False,
                exento_en_subcuadra_actual=True,
            )
        else:
            # El vehiculo tiene exencion parcial pero esta FUERA de su zona.
            # necesita_infraccion() devuelve True cuando exento_en_subcuadra_actual is False,
            # por lo que el template mostrara el boton de infraccionar.
            return ResultadoVerificacion(
                patente=patente,
                estado=EstadoVehiculo.EXENTO_PARCIAL,
                subcuadras_exentas=subcuadras_del_vehiculo,
                estacionamiento_activo=False,
                exento_en_subcuadra_actual=False,
                registrar_infraccion_url=_url_infraccion(patente),
            )

    # 5. TOLERANCIA del inspector (entre verificaciones sucesivas)
    if verificacion_anterior:
        tiempo_desde_ultima = timezone.now() - verificacion_anterior.fecha
        if tiempo_desde_ultima <= timedelta(minutes=_TOLERANCIA_INSPECTOR_MINUTOS):
            return ResultadoVerificacion(
                patente=patente,
                estado=EstadoVehiculo.PENDIENTE_PAGO,
                subcuadras_exentas=[],
                estacionamiento_activo=False,
            )

    # 6. INFRACCIÓN RECIENTE — ya existe un acta en los últimos N minutos.
    # Sin este chequeo el inspector vería el botón INFRACCIONAR y recién
    # descubriría el duplicado al enviar el formulario (mala UX).
    if municipio:
        hace_n_min = timezone.now() - timedelta(minutes=MINUTOS_ENTRE_INFRACCIONES)
        infraccion_reciente = (
            Infraccion.objects
            .filter(vehiculo=vehiculo, municipio=municipio, creado_en__gte=hace_n_min)
            .order_by("-creado_en")
            .first()
        )
        if infraccion_reciente:
            segundos_transcurridos = (timezone.now() - infraccion_reciente.creado_en).total_seconds()
            minutos_hasta = max(1, int((MINUTOS_ENTRE_INFRACCIONES * 60 - segundos_transcurridos) / 60) + 1)
            return ResultadoVerificacion(
                patente=patente,
                estado=EstadoVehiculo.INFRACCION_RECIENTE,
                estacionamiento_activo=False,
                minutos_hasta_siguiente=minutos_hasta,
            )

    # 7. IMPAGO
    return ResultadoVerificacion(
        patente=patente,
        estado=EstadoVehiculo.IMPAGO,
        estacionamiento_activo=False,
        registrar_infraccion_url=_url_infraccion(patente),
    )
