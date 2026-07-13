# app_estacionamiento/use_cases/estacionar_vehiculo.py
from decimal import Decimal
from django.db import transaction

from app_estacionamiento.factories import EstacionamientoFactory
from app_estacionamiento.models import Usuario, VehiculoUsuario, Tarifa
from app_estacionamiento.domain.vehiculo_policy import VehiculoPolicy
from app_estacionamiento.domain.saldo_policy import SaldoPolicy

from app_estacionamiento.services.horarios import obtener_tarifa_hora
from app_estacionamiento.services.saldo import debitar_saldo_conductor

REDIRECT_OK        = "inicio_usuarios"
REDIRECT_SIN_SALDO = "mp_iniciar_carga"


def ejecutar_estacionamiento(usuario, vehiculo, subcuadra, duracion):

    try:
        duracion = Decimal(duracion)
        if duracion <= 0:
            raise ValueError()
    except Exception:
        return {
            "ok": False,
            "redirect": "inicio",
            "warnings": ["Duracion invalida"]
        }

    tarifa_obj  = Tarifa.objects.filter(municipio=usuario.municipio).first()
    # obtener_tarifa_hora centraliza la selección auto/moto con fallback $100
    tarifa_hora = obtener_tarifa_hora(tarifa_obj, vehiculo)
    costo       = duracion * tarifa_hora

    relaciones = VehiculoUsuario.objects.filter(vehiculo=vehiculo)
    warnings   = VehiculoPolicy.generar_warnings(usuario, vehiculo, relaciones)

    if not SaldoPolicy.tiene_saldo(usuario, costo):
        return {
            "ok": False,
            "redirect": REDIRECT_SIN_SALDO,
            "warnings": warnings
        }

    with transaction.atomic():

        usuario_db = Usuario.objects.select_for_update().get(id=usuario.id)

        if not SaldoPolicy.tiene_saldo(usuario_db, costo):
            return {
                "ok": False,
                "redirect": REDIRECT_SIN_SALDO,
                "warnings": warnings
            }

        EstacionamientoFactory.crear(
            usuario=usuario_db,
            vehiculo=vehiculo,
            subcuadra=subcuadra,
            duracion=duracion,
            costo_base=costo
        )

        # debitar_saldo_conductor descuenta saldo y registra el egreso en caja.
        # usuario_db ya está bloqueado con select_for_update(), no abre nueva transacción.
        debitar_saldo_conductor(
            conductor=usuario_db,
            monto=costo,
            descripcion="Estacionamiento",
        )

    return {
        "ok": True,
        "redirect": REDIRECT_OK,
        "warnings": warnings
    }
