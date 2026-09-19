# app_estacionamiento/services/descuentos_verificados.py
"""
Descuento para conductores verificados.

El superadmin puede configurar en cada municipio un porcentaje de descuento
sobre el costo de estacionamiento para conductores que verificaron su identidad.
El alcance puede ser "todos los verificados" o "solo verificados vecinos del municipio".

Esta lógica está aislada aquí para que sea fácil ajustarla sin tocar el use case.
"""

from decimal import Decimal


def calcular_descuento_conductor(conductor, municipio):
    """
    Retorna el porcentaje de descuento que corresponde al conductor en este municipio.

    Reglas:
      1. Si municipio.descuento_verificados_pct es None/0 → sin descuento (retorna 0).
      2. Si el conductor no tiene es_verificado=True → sin descuento.
      3. Si municipio.descuento_solo_vecinos=True y el conductor no tiene es_vecino=True
         → sin descuento.
      4. Si pasa todos los filtros → retorna el porcentaje configurado.

    Args:
        conductor: instancia de Usuario (el conductor).
        municipio: instancia de Municipio.

    Returns:
        Decimal — porcentaje de descuento (0 si no aplica, > 0 si aplica).
    """
    pct = municipio.descuento_verificados_pct if municipio else None

    # Sin módulo configurado
    if not pct or pct <= 0:
        return Decimal("0")

    # Solo conductores verificados
    if not getattr(conductor, "es_verificado", False):
        return Decimal("0")

    # Alcance restringido a vecinos
    if municipio.descuento_solo_vecinos and not getattr(conductor, "es_vecino", False):
        return Decimal("0")

    return Decimal(str(pct))


def aplicar_descuento_conductor(costo, conductor, municipio):
    """
    Aplica el descuento de verificado sobre un costo de estacionamiento.

    Args:
        costo    (Decimal): costo original.
        conductor:          instancia de Usuario.
        municipio:          instancia de Municipio.

    Returns:
        dict con:
          costo_final   (Decimal) — costo después del descuento
          descuento_pct (Decimal) — porcentaje aplicado (0 si no aplica)
          motivo        (str)     — descripción legible, vacío si no aplica
    """
    pct = calcular_descuento_conductor(conductor, municipio)

    if pct <= 0:
        return {
            "costo_final":   costo,
            "descuento_pct": Decimal("0"),
            "motivo":        "",
        }

    costo_final = (costo * (1 - pct / 100)).quantize(Decimal("0.01"))

    alcance = "vecino verificado" if municipio.descuento_solo_vecinos else "conductor verificado"
    motivo = f"Descuento {pct:.0f}% por {alcance}"

    return {
        "costo_final":   costo_final,
        "descuento_pct": pct,
        "motivo":        motivo,
    }
