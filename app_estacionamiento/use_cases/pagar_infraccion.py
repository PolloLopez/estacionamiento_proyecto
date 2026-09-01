# app_estacionamiento/use_cases/pagar_infraccion.py
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from app_estacionamiento.models import Infraccion, ModuloMunicipio, Tarifa, Usuario
from app_estacionamiento.services.saldo import debitar_saldo_conductor
from app_estacionamiento.services.infracciones import (
    calcular_descuento_infraccion,
    calcular_estado_tolerancia,
)


def ejecutar(usuario, infraccion):
    """
    Paga una infraccion del conductor con su saldo.

    Tolerancia de gracia: si el conductor paga dentro de los primeros
    X minutos (configurado en municipio.tolerancia_multa_minutos),
    la infraccion se ANULA automaticamente sin cobrar nada.
    Incluye un margen de MARGEN_TOLERANCIA_SEGUNDOS para evitar cobrar
    por diferencias de pocos segundos.

    Retorna la infraccion actualizada con atributo extra:
      - infraccion.anulada_por_gracia (True si se anulo, False si se cobro)

    Usa select_for_update() para evitar race conditions de doble pago.
    """
    with transaction.atomic():
        # Bloquear filas para prevenir doble pago concurrente
        infraccion_locked = Infraccion.objects.select_for_update().get(pk=infraccion.pk)
        usuario_locked    = Usuario.objects.select_for_update().get(pk=usuario.pk)

        if infraccion_locked.estado != "pendiente":
            raise Exception("La infraccion ya fue procesada")

        # ── Tolerancia de gracia ─────────────────────────────────────────────
        # calcular_estado_tolerancia incluye MARGEN_TOLERANCIA_SEGUNDOS=60
        # para no cobrar por diferencias de pocos segundos.
        ahora      = timezone.now()
        estado_tol = calcular_estado_tolerancia(
            infraccion_locked,
            infraccion_locked.municipio,
            ahora=ahora,
        )

        if estado_tol["dentro_tolerancia"]:
            # Anular sin cobrar
            infraccion_locked.estado     = "anulada"
            infraccion_locked.fecha_pago = ahora
            infraccion_locked.save()
            infraccion_locked.anulada_por_gracia = True
            return infraccion_locked

        # ── Descuento por pago voluntario (módulo premium) ───────────────────
        # Si el municipio tiene activo el módulo descuentos_voluntarios,
        # se consulta la tarifa y se aplica el descuento que corresponda según
        # el tiempo transcurrido desde el acta.
        modulo_descuento_activo = ModuloMunicipio.objects.filter(
            municipio=infraccion_locked.municipio,
            modulo="descuentos_voluntarios",
            activo=True,
        ).exists()

        monto_a_cobrar = infraccion_locked.monto
        descuento_pct  = Decimal("0")
        descuento_motivo = ""

        if modulo_descuento_activo:
            tarifa = Tarifa.objects.filter(
                municipio=infraccion_locked.municipio
            ).first()
            resultado = calcular_descuento_infraccion(
                infraccion_locked, tarifa, ahora=ahora
            )
            monto_a_cobrar   = resultado["monto_final"]
            descuento_pct    = resultado["descuento_pct"]
            descuento_motivo = resultado["motivo"]

        # ── Cobro normal ─────────────────────────────────────────────────────
        # debitar_saldo_conductor valida saldo, descuenta y registra el egreso.
        # usuario_locked ya esta bloqueado con select_for_update().
        debitar_saldo_conductor(
            conductor=usuario_locked,
            monto=monto_a_cobrar,
            descripcion=f"Pago infraccion #{infraccion_locked.id} — {infraccion_locked.vehiculo.patente}",
        )

        infraccion_locked.estado                = "pagada"
        infraccion_locked.fecha_pago            = ahora
        infraccion_locked.monto_pagado          = monto_a_cobrar
        infraccion_locked.descuento_pct_aplicado = descuento_pct
        infraccion_locked.descuento_motivo       = descuento_motivo
        infraccion_locked.save(update_fields=[
            "estado", "fecha_pago",
            "monto_pagado", "descuento_pct_aplicado", "descuento_motivo",
        ])

    infraccion_locked.anulada_por_gracia = False
    return infraccion_locked
