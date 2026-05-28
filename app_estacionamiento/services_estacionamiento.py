# app_estacionamiento/services_estacionamiento.py
from decimal import Decimal
from django.db import transaction
from app_estacionamiento.factories import EstacionamientoFactory
from app_estacionamiento.models import MovimientoCaja, Usuario, VehiculoUsuario

TARIFA_BASE = Decimal("100")


def estacionar(usuario, vehiculo, subcuadra, duracion):

    costo = Decimal(duracion) * TARIFA_BASE

    warnings = []

    # =====================================
    # WARNINGS (antes estaban en la vista)
    # =====================================

    relaciones = VehiculoUsuario.objects.filter(vehiculo=vehiculo)

    if relaciones.filter(es_propietario=True).exists() and not relaciones.filter(usuario=usuario, es_propietario=True).exists():
        warnings.append("🚨 Este vehículo tiene otro propietario")

    if relaciones.exclude(usuario=usuario).exists():
        warnings.append("⚠️ Vehículo asociado a múltiples usuarios")

    relacion = VehiculoUsuario.objects.filter(
        usuario=usuario,
        vehiculo=vehiculo
    ).first()

    if relacion and not relacion.verificado:
        warnings.append("⛔ Usuario no verificado")

    # =====================================
    # VALIDACIÓN SALDO
    # =====================================

    if usuario.saldo < costo:
        return {
            "ok": False,
            "redirect": "consultar_deuda",
            "warnings": warnings
        }

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