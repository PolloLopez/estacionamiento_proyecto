# app_estacionamiento/use_cases/estacionar_vehiculo.py
from decimal import Decimal
from urllib import request
from django.db import transaction

from app_estacionamiento.factories import EstacionamientoFactory
from app_estacionamiento.models import Usuario, MovimientoCaja, VehiculoUsuario
from app_estacionamiento.domain.vehiculo_policy import VehiculoPolicy
from app_estacionamiento.domain.saldo_policy import SaldoPolicy

from app_estacionamiento.use_cases.registrar_movimiento import ejecutar as registrar_movimiento

TARIFA_BASE = Decimal("100")
REDIRECT_OK = "inicio"
REDIRECT_SIN_SALDO = "consultar_deuda"

def ejecutar_estacionamiento(usuario, vehiculo, subcuadra, duracion):

    try:
        duracion = Decimal(duracion)
        if duracion <= 0:
            raise ValueError()
    except:
        return {
            "ok": False,
            "redirect": "inicio",
            "warnings": ["Duración inválida"]
        }

    costo = duracion * TARIFA_BASE

    relaciones = VehiculoUsuario.objects.filter(vehiculo=vehiculo)

    warnings = VehiculoPolicy.generar_warnings(
        usuario,
        vehiculo,
        relaciones
    )

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

        usuario_db.saldo -= costo
        usuario_db.save()

        registrar_movimiento(
            usuario=usuario_db,
            monto=costo,
            tipo="egreso",
            descripcion="Estacionamiento"
        )

    return {
        "ok": True,
        "redirect": REDIRECT_OK,
        "warnings": warnings
    }