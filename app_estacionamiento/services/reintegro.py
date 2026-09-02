# app_estacionamiento/services/reintegro.py
"""
Lógica de negocio del módulo "Reintegro de estacionamiento para vecinos".

El municipio puede ofrecer un crédito de saldo a los conductores por los
primeros N minutos de cada estacionamiento. El alcance lo elige el superadmin:
- "todos"      → cualquier conductor activo del municipio
- "residentes" → solo conductores marcados como es_residente_verificado=True

Reglas:
- El módulo debe estar activo en ModuloMunicipio.
- Hay un límite diario de reintegros por conductor (reintegro_max_por_dia).
- El monto es proporcional a la tarifa vigente: (tarifa_hora / 60) * minutos.
- Esta función se llama dentro del transaction.atomic() de ejecutar_estacionamiento,
  con el conductor ya bloqueado con select_for_update().
"""

from decimal import Decimal, ROUND_HALF_UP

from django.utils import timezone

from app_estacionamiento.models import ModuloMunicipio, Reintegro


def modulo_reintegro_activo(municipio):
    """Retorna True si el módulo está habilitado para el municipio."""
    return ModuloMunicipio.objects.filter(
        municipio=municipio, modulo="reintegro_residentes", activo=True
    ).exists()


def calcular_monto_reintegro(municipio, tarifa_hora):
    """
    Calcula el monto a reintegrar.
    Usa tarifa_hora (Decimal) y municipio.reintegro_minutos.
    Devuelve Decimal redondeado a 2 decimales.
    """
    if not tarifa_hora or tarifa_hora <= 0:
        return Decimal("0")
    monto = (tarifa_hora / 60 * municipio.reintegro_minutos)
    return monto.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def puede_reintegrar_hoy(conductor, municipio):
    """
    Verifica si el conductor no superó el límite diario de reintegros.
    """
    hoy = timezone.localtime().date()
    cantidad = Reintegro.objects.filter(
        conductor=conductor,
        municipio=municipio,
        creado_en__date=hoy,
    ).count()
    return cantidad < municipio.reintegro_max_por_dia


def aplica_alcance(conductor, municipio):
    """
    Verifica si el conductor cumple el alcance configurado:
    - "todos": cualquier conductor activo
    - "residentes": solo los verificados como vecinos
    """
    if municipio.reintegro_alcance == "todos":
        return True
    return conductor.es_residente_verificado


def aplicar_reintegro(conductor, municipio, estacionamiento, tarifa_hora):
    """
    Acredita el reintegro al conductor si se cumplen todas las condiciones.

    Debe llamarse dentro de un transaction.atomic() con el conductor ya
    bloqueado con select_for_update().

    Retorna dict: {"reintegrado": bool, "monto": Decimal}
    """
    if not modulo_reintegro_activo(municipio):
        return {"reintegrado": False, "monto": Decimal("0")}

    if not aplica_alcance(conductor, municipio):
        return {"reintegrado": False, "monto": Decimal("0")}

    if not puede_reintegrar_hoy(conductor, municipio):
        return {"reintegrado": False, "monto": Decimal("0")}

    monto = calcular_monto_reintegro(municipio, tarifa_hora)
    if monto <= 0:
        return {"reintegrado": False, "monto": Decimal("0")}

    # Acreditar saldo y dejar registro contable
    conductor.saldo += monto
    conductor.save(update_fields=["saldo"])
    Reintegro.objects.create(
        conductor=conductor,
        municipio=municipio,
        estacionamiento=estacionamiento,
        monto=monto,
    )

    return {"reintegrado": True, "monto": monto}
