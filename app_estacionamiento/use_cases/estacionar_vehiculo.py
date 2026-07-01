# app_estacionamiento/use_cases/estacionar_vehiculo.py
from decimal import Decimal
from django.db import transaction

from app_estacionamiento.factories import EstacionamientoFactory
from app_estacionamiento.models import Usuario, MovimientoCaja, VehiculoUsuario, Tarifa
from app_estacionamiento.domain.vehiculo_policy import VehiculoPolicy
from app_estacionamiento.domain.saldo_policy import SaldoPolicy

from app_estacionamiento.use_cases.registrar_movimiento import ejecutar as registrar_movimiento

TARIFA_BASE_FALLBACK = Decimal("100")
REDIRECT_OK = "inicio"
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

    tarifa_obj = Tarifa.objects.filter(municipio=usuario.municipio).first()

    # Seleccionar tarifa segun tipo de vehiculo
    if tarifa_obj:
        es_moto = getattr(vehiculo, "tipo", "auto") == "moto"
        precio_moto = getattr(tarifa_obj, "precio_por_hora_moto", None)
        if es_moto and precio_moto and precio_moto > 0:
            tarifa_hora = precio_moto
        else:
            tarifa_hora = tarifa_obj.precio_por_hora
    else:
        tarifa_hora = TARIFA_BASE_FALLBACK

    costo = duracion * tarifa_hora

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
