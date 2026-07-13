# app_estacionamiento/utils.py
"""
Funciones utilitarias compartidas entre módulos.

Aquí viven helpers que no pertenecen a un rol específico
y son reutilizados por varias vistas y servicios.
"""

from datetime import timedelta

from django.utils import timezone

from app_estacionamiento.models import (
    DiaEspecial,
    Estacionamiento,
    HorarioEstacionamiento,
    Subcuadra,
)


def get_subcuadra_default(municipio):
    """
    Retorna la subcuadra "Zona Única" del municipio.
    La crea automáticamente si no existe (para conductores sin calle asignada).
    """
    subcuadra, _ = Subcuadra.objects.get_or_create(
        calle="Zona Única",
        altura=0,
        municipio=municipio
    )
    return subcuadra


def puede_estacionar_ahora(municipio):
    """
    Verifica si el horario del municipio permite estacionar en este momento.
    Tiene en cuenta días especiales (feriados) y el horario semanal.

    Devuelve:
        (permitido: bool, mensaje_error: str | None)

    Usa caché de 1 hora para no repetir queries por cada verificación.
    """
    from django.core.cache import cache

    ahora       = timezone.localtime()
    hoy_fecha   = ahora.date()
    hoy_dia     = ahora.weekday()   # 0=Lunes … 6=Domingo
    hora_actual = ahora.time()

    cache_key = f"puede_estacionar_{municipio.id}_{hoy_fecha}_{ahora.hour}"
    resultado_cached = cache.get(cache_key)
    if resultado_cached is not None:
        return resultado_cached

    # Día especial sin cobro activo → libre de estacionamiento
    dia_especial = DiaEspecial.objects.filter(
        municipio=municipio, fecha=hoy_fecha
    ).first()
    if dia_especial and not dia_especial.cobro_activo:
        resultado = (False, f"Hoy es {dia_especial.descripcion}. No hay cobro de estacionamiento.")
        cache.set(cache_key, resultado, timeout=3600)
        return resultado

    # Horario semanal configurado para este día
    horario = HorarioEstacionamiento.objects.filter(
        municipio=municipio, dia_semana=hoy_dia, activo=True
    ).first()

    if horario is None:
        resultado = (True, None)
        cache.set(cache_key, resultado, timeout=3600)
        return resultado

    if hora_actual < horario.hora_inicio or hora_actual > horario.hora_fin:
        resultado = (False, (
            f"El estacionamiento está habilitado de "
            f"{horario.hora_inicio.strftime('%H:%M')} a "
            f"{horario.hora_fin.strftime('%H:%M')}. "
            f"Actualmente son las {hora_actual.strftime('%H:%M')}."
        ))
        cache.set(cache_key, resultado, timeout=3600)
        return resultado

    resultado = (True, None)
    cache.set(cache_key, resultado, timeout=3600)
    return resultado


def calcular_opciones_duracion(municipio, tarifa_hora, hora_inicio_est=None, duracion_actual_h=0):
    """
    Retorna lista de dicts {horas, label, costo} con múltiplos de 30 min disponibles
    hasta el cierre del día para el municipio.

    Parámetros:
        municipio: instancia de Municipio
        tarifa_hora: precio por hora (Decimal)
        hora_inicio_est: datetime de inicio del estacionamiento actual (para renovar)
        duracion_actual_h: horas ya pagadas (para renovar)

    Devuelve:
        Lista de opciones disponibles, vacía si no queda tiempo.
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
        minutos_disponibles = 8 * 60  # Sin horario → máximo 8 horas

    opciones = []
    for n in range(1, 17):      # 30 min × 1..16 → hasta 8 h
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

    Se llama en inicio_usuarios de forma reactiva (sin tarea periódica).
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
            subcuadra__municipio=municipio
        )
        for est in activos:
            finalizar_estacionamiento_uc(est)