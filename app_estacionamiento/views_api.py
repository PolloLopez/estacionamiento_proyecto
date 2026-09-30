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

from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET

from .decorators import require_login
from .models import AbonoMensual, Estacionamiento, Tarifa
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
        "url_renovar":      f"/estacionar/renovar/{est.id}/",
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

    # Saldo y verificación de mínimo para 1 hora
    saldo      = obtener_saldo_conductor(usuario, usuario.municipio)
    tarifa     = Tarifa.objects.filter(municipio=usuario.municipio).first() if usuario.municipio else None
    costo_hora = float(tarifa.precio_por_hora) if tarifa else None
    saldo_insuficiente = (
        not dia_libre_hoy
        and costo_hora is not None
        and float(saldo) < costo_hora
    )

    return JsonResponse({
        "saldo":              float(saldo),
        "puede_estacionar":   puede_estacionar,
        "mensaje_horario":    mensaje_horario,
        "dia_libre_hoy":      dia_libre_hoy,
        "saldo_insuficiente": saldo_insuficiente,
        "costo_hora_min":     costo_hora,
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
