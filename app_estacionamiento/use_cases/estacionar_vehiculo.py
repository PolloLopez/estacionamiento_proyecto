# app_estacionamiento/use_cases/estacionar_vehiculo.py
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from app_estacionamiento.factories import EstacionamientoFactory
from app_estacionamiento.models import Infraccion, Usuario, VehiculoUsuario, Tarifa
from app_estacionamiento.domain.vehiculo_policy import VehiculoPolicy
from app_estacionamiento.domain.saldo_policy import SaldoPolicy

from app_estacionamiento.services.horarios import obtener_tarifa_hora
from app_estacionamiento.services.saldo import debitar_saldo_conductor
from app_estacionamiento.services.infracciones import calcular_estado_tolerancia

REDIRECT_OK        = "inicio_usuarios"
REDIRECT_SIN_SALDO = "mp_iniciar_carga"


def ejecutar_estacionamiento(usuario, vehiculo, subcuadra, duracion):
    """
    Registra un estacionamiento para el conductor.

    Flujo:
    1. Valida duracion y saldo (optimista sin lock).
    2. Dentro de transaction.atomic() con select_for_update:
       a. Revalida saldo (con lock para evitar race condition).
       b. Chequea si el vehiculo tiene infraccion pendiente:
          - Dentro de tolerancia → anula la infraccion sin cobrar.
          - Fuera de tolerancia  → deja la infraccion pendiente,
            retorna info para mostrar notificacion al conductor.
       c. Crea el Estacionamiento y debita el saldo.

    Retorna dict con:
      - ok       (bool)
      - redirect (str)    — nombre de URL
      - warnings (list)   — avisos de VehiculoPolicy
      - info_infraccion   — None, o dict con datos de la infraccion detectada
    """

    try:
        duracion = Decimal(duracion)
        if duracion <= 0:
            raise ValueError()
    except Exception:
        return {
            "ok": False,
            "redirect": "inicio",
            "warnings": [],
            "info_infraccion": None,
        }

    tarifa_obj  = Tarifa.objects.filter(municipio=usuario.municipio).first()
    tarifa_hora = obtener_tarifa_hora(tarifa_obj, vehiculo)
    costo       = duracion * tarifa_hora

    relaciones = VehiculoUsuario.objects.filter(vehiculo=vehiculo)
    warnings   = VehiculoPolicy.generar_warnings(usuario, vehiculo, relaciones)

    if not SaldoPolicy.tiene_saldo(usuario, costo):
        return {
            "ok": False,
            "redirect": REDIRECT_SIN_SALDO,
            "warnings": warnings,
            "info_infraccion": None,
        }

    with transaction.atomic():

        usuario_db = Usuario.objects.select_for_update().get(id=usuario.id)

        if not SaldoPolicy.tiene_saldo(usuario_db, costo):
            return {
                "ok": False,
                "redirect": REDIRECT_SIN_SALDO,
                "warnings": warnings,
                "info_infraccion": None,
            }

        # ── Chequeo de infraccion pendiente ───────────────────────────────────
        # Si el vehiculo tiene una infraccion pendiente en este municipio,
        # aplicar la logica de tolerancia de gracia.
        ahora = timezone.now()
        info_infraccion = None

        if usuario.municipio:
            infraccion_pendiente = Infraccion.objects.filter(
                vehiculo=vehiculo,
                municipio=usuario.municipio,
                estado="pendiente",
            ).order_by("-creado_en").first()

            if infraccion_pendiente:
                estado_tol = calcular_estado_tolerancia(
                    infraccion_pendiente,
                    usuario.municipio,
                    ahora=ahora,
                )

                if estado_tol["dentro_tolerancia"]:
                    # Anular la infraccion sin cobrar
                    infraccion_pendiente.estado     = "anulada"
                    infraccion_pendiente.fecha_pago = ahora
                    infraccion_pendiente.save()
                    info_infraccion = {
                        "anulada":           True,
                        "tolerancia_min":    estado_tol["tolerancia_min"],
                        "hora_verificacion": estado_tol["hora_verificacion"],
                        "hora_fin_gracia":   estado_tol["hora_fin_gracia"],
                    }
                else:
                    # Dejar pendiente — conductor puede pagarla desde la app
                    info_infraccion = {
                        "anulada":              False,
                        "infraccion_id":        infraccion_pendiente.id,
                        "monto":                infraccion_pendiente.monto,
                        "tolerancia_min":       estado_tol["tolerancia_min"],
                        "hora_verificacion":    estado_tol["hora_verificacion"],
                        "hora_fin_gracia":      estado_tol["hora_fin_gracia"],
                        "hora_estacionamiento": ahora,
                    }

        EstacionamientoFactory.crear(
            usuario=usuario_db,
            vehiculo=vehiculo,
            subcuadra=subcuadra,
            duracion=duracion,
            costo_base=costo
        )

        # debitar_saldo_conductor descuenta saldo y registra el egreso en caja.
        # usuario_db ya esta bloqueado con select_for_update(), no abre nueva transaccion.
        debitar_saldo_conductor(
            conductor=usuario_db,
            monto=costo,
            descripcion="Estacionamiento",
        )

    return {
        "ok": True,
        "redirect": REDIRECT_OK,
        "warnings": warnings,
        "info_infraccion": info_infraccion,
    }
