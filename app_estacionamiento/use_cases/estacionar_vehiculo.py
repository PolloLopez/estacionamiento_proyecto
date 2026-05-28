# app_estacionamiento/use_cases/estacionar_vehiculo.py
from decimal import Decimal
from django.db import transaction

from app_estacionamiento.factories import EstacionamientoFactory
from app_estacionamiento.models import Usuario, MovimientoCaja, VehiculoUsuario

TARIFA_BASE = Decimal("100")
REDIRECT_OK = "inicio"
REDIRECT_SIN_SALDO = "consultar_deuda"

def ejecutar(usuario, vehiculo, subcuadra, duracion):

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

    warnings = []

    # ============================
    # WARNINGS (reglas de negocio)
    # ============================
    relaciones = VehiculoUsuario.objects.filter(vehiculo=vehiculo)

    if relaciones.filter(es_propietario=True).exists() and not relaciones.filter(usuario=usuario, es_propietario=True).exists():
        warnings.append("🚨 Otro propietario registrado")

    if relaciones.exclude(usuario=usuario).exists():
        warnings.append("⚠️ Múltiples usuarios asociados")

    relacion = relaciones.filter(
        usuario=usuario
    ).first()

    if relacion and not relacion.verificado:
        warnings.append("⛔ Usuario no verificado")

    # ============================
    # VALIDACIÓN SALDO
    # ============================
    if usuario.saldo < costo:
        return {
            "ok": False,
            "redirect": "consultar_deuda",
            "warnings": warnings
        }

    # ============================
    # TRANSACTION CORE
    # ============================
    with transaction.atomic():

        usuario = Usuario.objects.select_for_update().get(id=usuario.id)

        if usuario.saldo < costo:
            return {
                "ok": False,
                "redirect": "consultar_deuda",
                "warnings": warnings
            }

        EstacionamientoFactory.crear(
            vehiculo,
            subcuadra,
            duracion,
            registrado_por=usuario
        )

        usuario.saldo -= costo
        usuario.save()

        MovimientoCaja.objects.create(
            usuario=usuario,
            monto=costo,
            tipo="egreso",
            descripcion="Estacionamiento"
        )

    return {
        "ok": True,
        "redirect": "inicio",
        "warnings": warnings
    }