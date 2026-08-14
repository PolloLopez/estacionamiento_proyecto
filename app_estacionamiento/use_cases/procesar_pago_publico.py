# app_estacionamiento/use_cases/procesar_pago_publico.py
"""
Procesa un pago público anónimo confirmado por MercadoPago.

Responsabilidades:
- Marcar el PagoPublico como 'aprobado'.
- Ejecutar la acción correspondiente al tipo:
    · infraccion      → marcar Infraccion como 'pagada'
    · estacionamiento → crear Estacionamiento (usuario=None)
    · abono           → crear AbonoMensual (conductor/vendedor=None)

Diseño:
- Idempotente: si el PagoPublico ya está en estado 'aprobado', no hace nada.
- Se llama desde mp_exitoso_publico (callback de la sesión del usuario)
  y desde mp_webhook (notificación asíncrona de MP como respaldo).
- Usa select_for_update() para evitar procesamiento doble concurrente.
"""

from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from app_estacionamiento.models import (
    PagoPublico, Infraccion, Vehiculo, Subcuadra, AbonoMensual,
)
from app_estacionamiento.factories import EstacionamientoFactory


def ejecutar(pago_publico_id: int, mp_payment_id: str, monto: Decimal):
    """
    Ejecuta el pago público correspondiente al PagoPublico con id=pago_publico_id.

    Parámetros:
    - pago_publico_id: ID del PagoPublico creado al iniciar el checkout.
    - mp_payment_id: ID del pago confirmado por MercadoPago.
    - monto: monto real procesado (del response de MP, no de la preferencia).

    Retorna el PagoPublico actualizado, o None si no se encontró.
    """
    with transaction.atomic():
        try:
            pago = PagoPublico.objects.select_for_update().get(pk=pago_publico_id)
        except PagoPublico.DoesNotExist:
            return None

        # Idempotencia: si ya fue procesado, no hacer nada
        if pago.estado == "aprobado":
            return pago

        # Guardar el payment_id de MP aunque el processing falle,
        # para evitar reprocessar si el webhook llega de nuevo
        pago.mp_payment_id = mp_payment_id
        pago.procesado_en  = timezone.now()
        pago.estado        = "aprobado"

        if pago.tipo == "infraccion":
            _pagar_infraccion(pago)

        elif pago.tipo == "estacionamiento":
            _crear_estacionamiento(pago)

        elif pago.tipo == "abono":
            _crear_abono(pago)

        pago.save()

    return pago


# ─────────────────────────────────────────────────────────────────────────────
# Handlers por tipo
# ─────────────────────────────────────────────────────────────────────────────

def _pagar_infraccion(pago: PagoPublico):
    """
    Marca la infracción asociada como 'pagada'.

    No aplica tolerancia de gracia: el usuario eligió explícitamente pagar,
    así que aunque esté dentro del período de gracia, se registra como pago
    y no como anulación.

    Si la infracción ya fue procesada (pagada o anulada), se ignora silenciosamente
    — la idempotencia del pago principal ya garantiza que no se repite.
    """
    if not pago.infraccion_id:
        return

    try:
        inf = Infraccion.objects.select_for_update().get(pk=pago.infraccion_id)
    except Infraccion.DoesNotExist:
        return

    if inf.estado != "pendiente":
        return  # ya procesada

    inf.estado     = "pagada"
    inf.fecha_pago = timezone.now()
    inf.save(update_fields=["estado", "fecha_pago"])


def _crear_estacionamiento(pago: PagoPublico):
    """
    Crea un Estacionamiento con usuario=None para el pago anónimo.

    Los datos (subcuadra, duracion_horas) se almacenaron en el PagoPublico
    al iniciar el checkout.

    Si faltan datos obligatorios, se ignora (no debería ocurrir en producción
    porque la vista valida antes de crear el PagoPublico).
    """
    if not pago.subcuadra_id or not pago.duracion_horas:
        return

    # Obtener o crear el Vehiculo (puede no existir si es el primer contacto del auto)
    vehiculo = _obtener_o_crear_vehiculo(pago)
    if not vehiculo:
        return

    try:
        subcuadra = Subcuadra.objects.get(pk=pago.subcuadra_id)
    except Subcuadra.DoesNotExist:
        return

    est = EstacionamientoFactory.crear(
        usuario=None,          # pago anónimo: sin usuario registrado
        vehiculo=vehiculo,
        subcuadra=subcuadra,
        duracion=pago.duracion_horas,
        costo_base=pago.monto,
    )

    # Vinculamos el estacionamiento creado al pago para trazabilidad
    pago.estacionamiento = est


def _crear_abono(pago: PagoPublico):
    """
    Crea un AbonoMensual sin conductor/vendedor vinculado.
    El inspector verá 'abono activo' al verificar la patente durante el mes pagado.
    """
    if not pago.mes_abono:
        return

    vehiculo = _obtener_o_crear_vehiculo(pago)
    if not vehiculo:
        return

    # unique_together = (vehiculo, municipio, mes) — evitar doble creación
    abono, creado = AbonoMensual.objects.get_or_create(
        vehiculo=vehiculo,
        municipio=pago.municipio,
        mes=pago.mes_abono,
        defaults={
            "monto":      pago.monto,
            "medio_pago": "mercadopago",
            "conductor":  None,
            "vendedor":   None,
        },
    )

    pago.abono = abono


def _obtener_o_crear_vehiculo(pago: PagoPublico):
    """
    Busca el Vehiculo por patente en el municipio.
    Si no existe, lo crea como tipo 'auto' (default).

    El conductor podrá vincularse a este vehículo más adelante si se registra.
    """
    patente = pago.patente.upper().strip()
    vehiculo, _ = Vehiculo.objects.get_or_create(
        patente=patente,
        defaults={
            "tipo":      "auto",
            "municipio": pago.municipio,
        },
    )
    return vehiculo
