# app_estacionamiento/services/horarios.py
"""
Lógica de negocio relacionada con horarios de estacionamiento.

Responsabilidades:
- Verificar si el municipio permite estacionar en el momento actual
- Calcular las opciones de duración disponibles según el horario y saldo
- Cerrar estacionamientos activos cuando venció el horario del día

Estas funciones manejan reglas de negocio del municipio (no son helpers puros de DB).
Antes vivían en utils.py.
"""

from datetime import timedelta

from django.utils import timezone

from app_estacionamiento.models import (
    DiaEspecial,
    Estacionamiento,
    HorarioEstacionamiento,
)


def puede_estacionar_ahora(municipio):
    """
    Verifica si el horario del municipio permite estacionar en este momento.
    Tiene en cuenta días especiales (feriados) y el horario semanal configurado.

    Usa caché de 1 hora para evitar queries repetidas en cada verificación.

    Retorna:
        (permitido: bool, mensaje_error: str | None)
        Si permitido es True, mensaje_error es None.
        Si permitido es False, mensaje_error explica por qué.
    """
    from django.core.cache import cache

    ahora       = timezone.localtime()
    hoy_fecha   = ahora.date()
    hoy_dia     = ahora.weekday()   # 0=Lunes … 6=Domingo
    hora_actual = ahora.time()

    cache_key        = f"puede_estacionar_{municipio.id}_{hoy_fecha}_{ahora.hour}"
    resultado_cached = cache.get(cache_key)
    if resultado_cached is not None:
        return resultado_cached

    # Día especial sin cobro → no se cobra estacionamiento
    dia_especial = DiaEspecial.objects.filter(
        municipio=municipio, fecha=hoy_fecha
    ).first()
    if dia_especial and not dia_especial.cobro_activo:
        resultado = (
            False,
            f"Hoy es {dia_especial.descripcion}. No hay cobro de estacionamiento.",
        )
        cache.set(cache_key, resultado, timeout=3600)
        return resultado

    # Horario semanal para el día actual
    horario = HorarioEstacionamiento.objects.filter(
        municipio=municipio, dia_semana=hoy_dia, activo=True
    ).first()

    if horario is None:
        # Sin horario configurado → libre de cobro todo el día
        resultado = (True, None)
        cache.set(cache_key, resultado, timeout=3600)
        return resultado

    if hora_actual < horario.hora_inicio or hora_actual > horario.hora_fin:
        resultado = (
            False,
            (
                f"El estacionamiento está habilitado de "
                f"{horario.hora_inicio.strftime('%H:%M')} a "
                f"{horario.hora_fin.strftime('%H:%M')}. "
                f"Actualmente son las {hora_actual.strftime('%H:%M')}."
            ),
        )
        cache.set(cache_key, resultado, timeout=3600)
        return resultado

    resultado = (True, None)
    cache.set(cache_key, resultado, timeout=3600)
    return resultado


def calcular_opciones_duracion(municipio, tarifa_hora, hora_inicio_est=None, duracion_actual_h=0):
    """
    Retorna lista de opciones de duración disponibles en múltiplos de 30 minutos,
    limitadas al cierre del horario del día.

    Parámetros:
        municipio: instancia de Municipio
        tarifa_hora: precio por hora (Decimal o float)
        hora_inicio_est: datetime de inicio del estacionamiento activo (para renovar)
        duracion_actual_h: horas ya pagadas en el estacionamiento activo

    Retorna:
        Lista de dicts [{horas, label, costo}].
        Lista vacía si no queda tiempo disponible.
    """
    from datetime import datetime as _dt

    ahora   = timezone.localtime()
    hoy_dia = ahora.weekday()

    horario = HorarioEstacionamiento.objects.filter(
        municipio=municipio, dia_semana=hoy_dia, activo=True
    ).first()

    if horario:
        cierre = timezone.make_aware(
            _dt.combine(ahora.date(), horario.hora_fin),
            timezone.get_current_timezone(),
        )
        if hora_inicio_est:
            vencimiento_actual = hora_inicio_est + timedelta(hours=float(duracion_actual_h))
            if vencimiento_actual >= cierre:
                return []
            minutos_disponibles = int((cierre - vencimiento_actual).total_seconds() / 60)
        else:
            minutos_disponibles = int((cierre - ahora).total_seconds() / 60)
    else:
        # Sin horario configurado → permitimos hasta 8 horas como máximo
        minutos_disponibles = 8 * 60

    opciones = []
    for n in range(1, 17):      # 30 min × 1..16 → hasta 8 horas
        horas   = n * 0.5
        minutos = int(horas * 60)
        if minutos > minutos_disponibles:
            break
        if horas < 1:
            label = "30 min"
        elif horas == 1.0:
            label = "1 hora"
        elif horas % 1 == 0:
            label = f"{int(horas)} horas"
        else:
            label = f"{int(horas)}h 30min"
        costo = round(float(horas) * float(tarifa_hora), 2)
        opciones.append({"horas": horas, "label": label, "costo": costo})

    return opciones


def cerrar_estacionamientos_vencidos_por_horario(municipio):
    """
    Cierra todos los estacionamientos activos del municipio
    si el horario de cobro ya terminó para el día de hoy.

    Se llama en inicio_usuarios de forma reactiva (sin tarea periódica programada).
    No hace nada si el horario sigue activo.
    """
    from app_estacionamiento.use_cases.finalizar_estacionamiento import (
        ejecutar as finalizar_estacionamiento_uc,
    )

    ahora       = timezone.localtime()
    hoy_dia     = ahora.weekday()
    hora_actual = ahora.time()

    horario = HorarioEstacionamiento.objects.filter(
        municipio=municipio, dia_semana=hoy_dia, activo=True
    ).first()

    if horario and hora_actual > horario.hora_fin:
        activos = Estacionamiento.objects.filter(
            estado="ACTIVO",
            subcuadra__municipio=municipio,
        )
        for est in activos:
            finalizar_estacionamiento_uc(est)
