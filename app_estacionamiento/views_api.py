"""
API JSON para el frontend React — conductores.

Cada endpoint devuelve JsonResponse puro (sin DRF, sin dependencias extra).
Los datos replican la lógica de las vistas de template pero en formato JSON.

Por qué un archivo separado de views_conductor.py:
    views_conductor.py ya tiene 1000+ líneas con lógica de template.
    Las vistas de API tienen una forma distinta (siempre JSON, sin render),
    y separarlas facilita encontrarlas, testearlas, y migrarlas a DRF
    cuando escale.

Convención de nombres:
    - api_conductor_*: endpoints del panel del conductor
    - Prefijo de URL: /api/conductor/
"""

from datetime import date, timedelta
from decimal import Decimal

from django.core.paginator import Paginator
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .decorators import require_login, require_role
from .models import AbonoMensual, Estacionamiento, Tarifa
from .services.saldo import debitar_saldo_conductor
from .services.horarios import calcular_opciones_duracion
from .utils import sanitizar_patente
from .services.saldo import obtener_saldo_conductor
from .services.horarios import (
    puede_estacionar_ahora,
    es_dia_libre_conductor,
    cerrar_estacionamientos_vencidos_por_horario,
)
from .use_cases.finalizar_estacionamiento import ejecutar as finalizar_estacionamiento_uc


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _serializar_estacionamiento(est):
    """
    Convierte un objeto Estacionamiento a dict JSON-serializable.

    hora_fin_unix: timestamp Unix de la expiración calculado en Python.
    El frontend no hace aritmética con horas; solo compara contra Date.now().
    """
    hora_fin = est.hora_inicio + timedelta(hours=float(est.duracion_horas))
    return {
        "id":               est.id,
        "patente":          est.vehiculo.patente,
        "tipo":             est.vehiculo.tipo,
        "subcuadra":        str(est.subcuadra) if est.subcuadra else None,
        "hora_inicio_unix": int(est.hora_inicio.timestamp()),
        "hora_fin_unix":    int(hora_fin.timestamp()),
        "duracion_horas":   float(est.duracion_horas),
        # URL para extender, lista para usar en el componente React sin conocer el patrón de URL
        "url_renovar":      reverse("usuarios_renovar_estacionamiento", args=[est.id]),
    }


def _estacionamientos_vigentes(usuario):
    """
    Devuelve los estacionamientos activos del conductor que todavía no vencieron.
    Auto-cierra silenciosamente los que ya expiraron (mismo comportamiento que la vista de template).
    """
    ahora = timezone.now()
    vigentes = []
    for est in (
        Estacionamiento.objects
        .filter(usuario=usuario, estado="ACTIVO")
        .select_related("vehiculo", "subcuadra")
        .order_by("-hora_inicio")
    ):
        expiracion = est.hora_inicio + timedelta(hours=float(est.duracion_horas))
        if ahora >= expiracion:
            finalizar_estacionamiento_uc(est)  # cierra en silencio, sin mensaje de Django
        else:
            vigentes.append(est)
    return vigentes


# ─── Endpoints ────────────────────────────────────────────────────────────────

@require_login
@require_GET
def api_conductor_dashboard(request):
    """
    GET /api/conductor/dashboard/

    Estado completo del conductor para el panel de inicio.
    Equivalente JSON de inicio_usuarios() — incluye el mismo auto-cierre.

    Úsalo para el mount inicial del componente React de inicio.
    Para polling del timer usá api_conductor_estacionamientos_activos (más liviano).
    """
    usuario = request.user

    # Auto-cierre por horario del municipio (igual que inicio_usuarios)
    if usuario.municipio:
        cerrar_estacionamientos_vencidos_por_horario(usuario.municipio)

    vigentes = _estacionamientos_vigentes(usuario)

    # Abonos activos del mes en curso
    mes_actual = date.today().replace(day=1)
    abonos = []
    if usuario.municipio:
        abonos = list(
            AbonoMensual.objects
            .filter(
                vehiculo__vehiculousuario__usuario=usuario,
                municipio=usuario.municipio,
                mes=mes_actual,
            )
            .select_related("vehiculo")
            .distinct()
        )

    # Horario y días libres
    puede_estacionar = True
    mensaje_horario  = None
    dia_libre_hoy    = False
    if usuario.municipio:
        puede_estacionar, mensaje_horario = puede_estacionar_ahora(usuario.municipio)
        dia_libre_hoy = es_dia_libre_conductor(usuario.municipio)
        # Día libre: el conductor puede estacionar sin costo aunque el horario diga "cerrado"
        if not puede_estacionar and dia_libre_hoy:
            puede_estacionar = True
            mensaje_horario  = None

    # Saldo y verificación de mínimo para la duración mínima del municipio
    saldo      = obtener_saldo_conductor(usuario, usuario.municipio)
    tarifa     = Tarifa.objects.filter(municipio=usuario.municipio).first() if usuario.municipio else None
    costo_hora = float(tarifa.precio_por_hora) if tarifa else None

    # duracion_minima_minutos vive en Municipio (campo del modelo, default 30)
    duracion_minima_min = (
        usuario.municipio.duracion_minima_minutos
        if usuario.municipio and hasattr(usuario.municipio, "duracion_minima_minutos")
        else 30
    )
    # Costo para la duración mínima (ej: 30 min → 0.5 * precio_hora)
    costo_duracion_minima = (
        round(costo_hora * duracion_minima_min / 60, 2) if costo_hora else None
    )
    saldo_insuficiente = (
        not dia_libre_hoy
        and costo_duracion_minima is not None
        and float(saldo) < costo_duracion_minima
    )

    return JsonResponse({
        "saldo":                  float(saldo),
        "puede_estacionar":       puede_estacionar,
        "mensaje_horario":        mensaje_horario,
        "dia_libre_hoy":          dia_libre_hoy,
        "saldo_insuficiente":     saldo_insuficiente,
        "costo_hora_min":         costo_hora,
        "duracion_minima_min":    duracion_minima_min,
        "costo_duracion_minima":  costo_duracion_minima,
        "estacionamientos_activos": [
            _serializar_estacionamiento(e) for e in vigentes
        ],
        "abonos_activos": [
            {
                "patente": a.vehiculo.patente,
                "tipo":    a.vehiculo.tipo,
                "mes":     a.mes.strftime("%Y-%m"),
            }
            for a in abonos
        ],
    })


@require_login
@require_GET
def api_conductor_historial(request):
    """
    GET /api/conductor/historial/?pagina=1&patente=AA123BB

    Historial paginado de estacionamientos del conductor (todos los estados).
    Equivalente JSON de historial_estacionamientos() en views_conductor.py.

    Parámetros opcionales:
        pagina   — número de página (default: 1, 20 registros por página)
        patente  — filtrar por patente exacta (mismo filtro que la vista Django)
    """
    usuario = request.user

    qs = (
        Estacionamiento.objects
        .filter(usuario=usuario)
        .select_related("vehiculo", "subcuadra")
        .order_by("-hora_inicio")
    )

    # Mismo filtro por patente que usa la vista Django
    patente_filtro = sanitizar_patente(request.GET.get("patente", ""))
    if patente_filtro:
        qs = qs.filter(vehiculo__patente=patente_filtro)

    paginator = Paginator(qs, 20)
    numero_pag = request.GET.get("pagina", 1)
    pagina = paginator.get_page(numero_pag)

    def serializar(est):
        # hora_fin_unix: usamos hora_fin real si el estacionamiento ya cerró,
        # o calculamos desde hora_inicio + duracion_horas si está activo.
        # Así el frontend no necesita saber cómo calcular la hora de fin.
        if est.hora_fin:
            hora_fin_unix = int(est.hora_fin.timestamp())
        else:
            hora_fin = est.hora_inicio + timedelta(hours=float(est.duracion_horas))
            hora_fin_unix = int(hora_fin.timestamp())

        return {
            "id":               est.id,
            "patente":          est.vehiculo.patente,
            "subcuadra":        str(est.subcuadra) if est.subcuadra else None,
            "hora_inicio_unix": int(est.hora_inicio.timestamp()),
            "hora_fin_unix":    hora_fin_unix,
            "duracion_horas":   float(est.duracion_horas),
            "costo":            float(est.costo_final if est.costo_final is not None else est.costo_base),
            "estado":           est.estado,
        }

    return JsonResponse({
        "estacionamientos":  [serializar(e) for e in pagina],
        "pagina":            pagina.number,
        "total_paginas":     paginator.num_pages,
        "total_registros":   paginator.count,
        "tiene_anterior":    pagina.has_previous(),
        "tiene_siguiente":   pagina.has_next(),
        "patente_filtro":    patente_filtro,
    })


@require_login
@require_GET
def api_conductor_opciones_renovar(request, est_id):
    """
    GET /api/conductor/estacionamiento/<est_id>/opciones-renovar/

    Devuelve las opciones de extensión disponibles para un estacionamiento activo.
    La lógica es idéntica a renovar_estacionamiento() de views_conductor.py:
    respeta el horario de cierre del municipio y usa fracciones de 30 min.

    El componente React las muestra como botones antes de que el usuario confirme.
    """
    usuario = request.user
    estacionamiento = get_object_or_404(
        Estacionamiento, id=est_id, usuario=usuario, estado="ACTIVO"
    )

    tarifa_obj  = Tarifa.objects.filter(municipio=usuario.municipio).first()
    tarifa_hora = tarifa_obj.precio_por_hora if tarifa_obj else Decimal("100")
    saldo       = obtener_saldo_conductor(usuario, usuario.municipio)

    opciones = calcular_opciones_duracion(
        municipio=usuario.municipio,
        tarifa_hora=tarifa_hora,
        hora_inicio_est=estacionamiento.hora_inicio,
        duracion_actual_h=float(estacionamiento.duracion_horas),
        duracion_minima_min=30,  # renovar siempre en bloques de 30 min
    )

    return JsonResponse({
        "saldo":             float(saldo),
        "tarifa_hora":       float(tarifa_hora),
        "hora_inicio_unix":  int(estacionamiento.hora_inicio.timestamp()),
        "duracion_actual_h": float(estacionamiento.duracion_horas),
        "opciones": [
            {
                "label":  op["label"],
                "horas":  float(op["horas"]),
                "costo":  float(op["costo"]),
            }
            for op in opciones
        ],
    })


@require_login
@require_POST
def api_conductor_renovar(request, est_id):
    """
    POST /api/conductor/estacionamiento/<est_id>/renovar/

    Extiende un estacionamiento activo descontando el saldo.
    Replica la lógica de renovar_estacionamiento() de views_conductor.py,
    pero devuelve JSON en lugar de redirigir.

    Body (JSON): { "horas_extra": 0.5 }

    Respuesta exitosa: { "ok": true, "nueva_hora_fin_unix": ... }
    Error: { "ok": false, "error": "..." }

    Por qué no abre su propia transacción en debitar_saldo_conductor:
    debitar_saldo_conductor() no abre transacción propia — debe llamarse dentro
    de un atomic() con select_for_update() ya activo (ver CLAUDE.md).
    """
    import json

    usuario = request.user

    try:
        body = json.loads(request.body)
        horas_extra = Decimal(str(body.get("horas_extra", 0)))
        if horas_extra <= 0:
            raise ValueError("horas_extra debe ser positivo")
    except Exception:
        return JsonResponse({"ok": False, "error": "Cantidad de horas inválida."}, status=400)

    estacionamiento = get_object_or_404(
        Estacionamiento, id=est_id, usuario=usuario, estado="ACTIVO"
    )

    tarifa_obj  = Tarifa.objects.filter(municipio=usuario.municipio).first()
    tarifa_hora = tarifa_obj.precio_por_hora if tarifa_obj else Decimal("100")
    costo_extra = horas_extra * tarifa_hora

    saldo_actual = obtener_saldo_conductor(usuario, usuario.municipio)
    if saldo_actual < costo_extra:
        return JsonResponse({
            "ok":    False,
            "error": f"Saldo insuficiente. Necesitás ${costo_extra:.2f} y tenés ${saldo_actual:.2f}.",
        }, status=400)

    with transaction.atomic():
        usuario_db = usuario.__class__.objects.select_for_update().get(id=usuario.id)
        try:
            debitar_saldo_conductor(
                conductor=usuario_db,
                monto=costo_extra,
                descripcion=f"Renovación {float(horas_extra):g}h — {estacionamiento.vehiculo.patente}",
                municipio=usuario.municipio,
            )
        except ValueError:
            return JsonResponse({"ok": False, "error": "Saldo insuficiente."}, status=400)

        estacionamiento.duracion_horas = estacionamiento.duracion_horas + horas_extra
        estacionamiento.save(update_fields=["duracion_horas"])

    nueva_hora_fin = estacionamiento.hora_inicio + timedelta(hours=float(estacionamiento.duracion_horas))
    return JsonResponse({
        "ok":                 True,
        "nueva_hora_fin_unix": int(nueva_hora_fin.timestamp()),
        "nueva_duracion_h":    float(estacionamiento.duracion_horas),
        "costo_debitado":      float(costo_extra),
    })


@require_login
@require_GET
def api_conductor_estacionamientos_activos(request):
    """
    GET /api/conductor/estacionamientos/activos/

    Endpoint liviano para polling del timer en React:
    solo devuelve los estacionamientos activos vigentes.

    El componente de inicio llama esto cada 30s para actualizar el countdown
    sin recargar el dashboard completo.
    """
    usuario  = request.user
    vigentes = _estacionamientos_vigentes(usuario)

    return JsonResponse({
        "estacionamientos": [_serializar_estacionamiento(e) for e in vigentes],
        "timestamp":        int(timezone.now().timestamp()),  # para que el cliente sepa cuán fresco es el dato
    })
