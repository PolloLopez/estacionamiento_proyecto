# app_estacionamiento/use_cases/transferir_saldo.py
"""
Use case: transferencia de saldo entre conductores del mismo municipio.

Flujo:
  - emisor inicia la transferencia → se debita inmediatamente (saldo reservado)
  - receptor acepta en 24h → saldo acreditado
  - receptor rechaza / emisor cancela / expira → saldo devuelto al emisor

Toda operación sobre saldo se hace dentro de transaction.atomic()
con select_for_update() sobre los dos conductores, para evitar race conditions.
"""

from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from app_estacionamiento.models import BilleteraConductor, TransferenciaSaldo, Usuario


MONTO_MINIMO     = Decimal("100")
HORAS_EXPIRACION = 24


def iniciar_transferencia(emisor, correo_receptor, monto_str):
    """
    Crea la transferencia debitando el monto del emisor.

    Retorna dict:
      {"ok": bool, "error": str|None, "transferencia": TransferenciaSaldo|None}
    """
    try:
        monto = Decimal(str(monto_str))
        if monto < MONTO_MINIMO:
            raise ValueError(f"El monto mínimo es ${MONTO_MINIMO}.")
    except Exception as e:
        return {"ok": False, "error": str(e), "transferencia": None}

    correo_receptor = correo_receptor.strip().lower()
    if correo_receptor == emisor.correo.lower():
        return {"ok": False, "error": "No podés transferirte saldo a vos mismo.", "transferencia": None}

    try:
        receptor = Usuario.objects.get(
            correo=correo_receptor,
            es_conductor=True,
            municipio=emisor.municipio,
        )
    except Usuario.DoesNotExist:
        return {
            "ok":    False,
            "error": f"No se encontró un conductor con ese correo en tu municipio.",
            "transferencia": None,
        }

    municipio = emisor.municipio

    with transaction.atomic():
        emisor_db = Usuario.objects.select_for_update().get(pk=emisor.pk)

        # Verificar y debitar de la billetera del municipio
        billetera_emisor, _ = BilleteraConductor.objects.select_for_update().get_or_create(
            conductor=emisor_db,
            municipio=municipio,
            defaults={"saldo": Decimal("0")},
        )
        if billetera_emisor.saldo < monto:
            return {
                "ok":    False,
                "error": f"Saldo insuficiente. Tenés ${billetera_emisor.saldo}.",
                "transferencia": None,
            }

        # Debitar al emisor de inmediato (saldo queda "reservado")
        billetera_emisor.saldo -= monto
        billetera_emisor.save(update_fields=["saldo"])

        ahora = timezone.now()
        transferencia = TransferenciaSaldo.objects.create(
            emisor=emisor_db,
            receptor=receptor,
            municipio=emisor.municipio,
            monto=monto,
            expira_en=ahora + timedelta(hours=HORAS_EXPIRACION),
        )

    return {"ok": True, "error": None, "transferencia": transferencia}


def responder_transferencia(usuario, transferencia_id, accion):
    """
    El receptor acepta o rechaza la transferencia.
    El emisor puede cancelarla (solo si sigue pendiente).

    accion: "aceptar" | "rechazar" | "cancelar"

    Retorna dict: {"ok": bool, "error": str|None}
    """
    if accion not in ("aceptar", "rechazar", "cancelar"):
        return {"ok": False, "error": "Acción inválida."}

    with transaction.atomic():
        try:
            transf = TransferenciaSaldo.objects.select_for_update().get(
                pk=transferencia_id, estado="pendiente"
            )
        except TransferenciaSaldo.DoesNotExist:
            return {"ok": False, "error": "Transferencia no encontrada o ya procesada."}

        ahora = timezone.now()

        # Verificar que quien responde tiene permiso
        if accion in ("aceptar", "rechazar") and transf.receptor_id != usuario.id:
            return {"ok": False, "error": "Solo el receptor puede aceptar o rechazar."}
        if accion == "cancelar" and transf.emisor_id != usuario.id:
            return {"ok": False, "error": "Solo el emisor puede cancelar."}

        # Verificar vigencia
        if ahora > transf.expira_en and accion != "cancelar":
            # Marcar como expirada y devolver saldo
            _devolver_al_emisor(transf)
            transf.estado       = "expirada"
            transf.respondido_en = ahora
            transf.save(update_fields=["estado", "respondido_en"])
            return {"ok": False, "error": "La transferencia ya expiró. El saldo fue devuelto."}

        if accion == "aceptar":
            # Acreditar al receptor en la billetera del municipio de la transferencia
            receptor_db = Usuario.objects.select_for_update().get(pk=transf.receptor_id)
            billetera_receptor, _ = BilleteraConductor.objects.select_for_update().get_or_create(
                conductor=receptor_db,
                municipio=transf.municipio,
                defaults={"saldo": Decimal("0")},
            )
            billetera_receptor.saldo += transf.monto
            billetera_receptor.save(update_fields=["saldo"])
            transf.estado        = "aceptada"
            transf.respondido_en = ahora
            transf.save(update_fields=["estado", "respondido_en"])

        elif accion in ("rechazar", "cancelar"):
            _devolver_al_emisor(transf)
            transf.estado        = "rechazada" if accion == "rechazar" else "cancelada"
            transf.respondido_en = ahora
            transf.save(update_fields=["estado", "respondido_en"])

    return {"ok": True, "error": None}


def _devolver_al_emisor(transf):
    """Devuelve el monto al emisor. Debe llamarse dentro de un atomic() con el emisor lockeado."""
    emisor_db = Usuario.objects.select_for_update().get(pk=transf.emisor_id)
    billetera, _ = BilleteraConductor.objects.select_for_update().get_or_create(
        conductor=emisor_db,
        municipio=transf.municipio,
        defaults={"saldo": Decimal("0")},
    )
    billetera.saldo += transf.monto
    billetera.save(update_fields=["saldo"])
