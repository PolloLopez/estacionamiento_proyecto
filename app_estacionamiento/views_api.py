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
from .models import AbonoMensual, Estacionamiento, Subcuadra, Tarifa, Vehiculo
from .services.saldo import debitar_saldo_conductor, obtener_saldo_conductor
from .services.horarios import (
    calcular_opciones_duracion,
    puede_estacionar_ahora,
    es_dia_libre_conductor,
    cerrar_estacionamientos_vencidos_por_horario,
)
from .services.descuentos_verificados import calcular_descuento_conductor
from .utils import get_subcuadra_default, sanitizar_patente
from .use_cases.estacionar_vehiculo import ejecutar_estacionamiento
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

    # Vehículos del conductor con infracciones pendientes y estado activo.
    # Mismo patrón que inicio_usuarios(): annotate evita N+1, activos se cruzan en Python.
    from django.db.models import Count, Q as DbQ
    vehiculo_ids_activos = {e.vehiculo_id for e in vigentes}
    # Comparamos por vehiculo_id (no por patente) para evitar diferencias de formato/case
    vehiculo_ids_con_abono = {a.vehiculo_id for a in abonos}
    vehiculos_qs = (
        Vehiculo.objects
        .filter(vehiculousuario__usuario=usuario)
        .annotate(
            infracciones_pendientes=Count(
                "infraccion",
                filter=DbQ(infraccion__estado="pendiente"),
            )
        )
        .distinct()
        .order_by("patente")
    )
    vehiculos_data = []
    for v in vehiculos_qs:
        estacionamiento_activo_id = next(
            (e.id for e in vigentes if e.vehiculo_id == v.id), None
        )
        vehiculos_data.append({
            "id":                       v.id,
            "patente":                  v.patente,
            "tipo":                     v.tipo,
            "tipo_display":             v.get_tipo_display(),
            "tiene_estacionamiento_activo": v.id in vehiculo_ids_activos,
            "estacionamiento_activo_id":    estacionamiento_activo_id,
            "tiene_abono_activo":       v.id in vehiculo_ids_con_abono,
            "infracciones_pendientes":  v.infracciones_pendientes,
            "exento":                   bool(getattr(v, "exento_global", False) or getattr(v, "exento_parcial", False)),
        })

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
        "vehiculos": vehiculos_data,
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


@require_login
@require_GET
def api_conductor_datos_estacionar(request):
    """
    GET /api/conductor/datos-estacionar/

    Datos necesarios para el formulario de estacionar React.
    Equivalente JSON del GET de estacionar_vehiculo() en views_conductor.py.

    Devuelve: vehículos, subcuadras, opciones de duración (auto y moto),
    saldo, tarifa efectiva, flags de horario y geoloc.
    """
    from datetime import date as _date

    usuario = request.user

    tarifa_obj  = Tarifa.objects.filter(municipio=usuario.municipio).first()
    tarifa_auto = tarifa_obj.precio_por_hora if tarifa_obj else Decimal("100")
    tarifa_moto = (
        tarifa_obj.precio_por_hora_moto
        if tarifa_obj and tarifa_obj.precio_por_hora_moto
        else tarifa_auto
    )

    dia_libre = bool(usuario.municipio and es_dia_libre_conductor(usuario.municipio))
    puede, msg_horario = puede_estacionar_ahora(usuario.municipio)
    fuera_de_horario = not puede and not dia_libre

    # Descuento por conductor verificado (mismo cálculo que views_conductor)
    if dia_libre:
        t_auto_ef     = Decimal("0")
        t_moto_ef     = Decimal("0")
        descuento_pct = 0
    else:
        desc = calcular_descuento_conductor(usuario, usuario.municipio)
        descuento_pct = float(desc)
        if desc > 0:
            factor    = 1 - desc / 100
            t_auto_ef = (tarifa_auto * factor).quantize(Decimal("0.01"))
            t_moto_ef = (tarifa_moto * factor).quantize(Decimal("0.01"))
        else:
            t_auto_ef = Decimal(str(tarifa_auto))
            t_moto_ef = Decimal(str(tarifa_moto))

    duracion_minima_min = tarifa_obj.duracion_minima_minutos if tarifa_obj else 30

    # Opciones de duración separadas por tipo de vehículo
    opciones_auto = calcular_opciones_duracion(
        usuario.municipio, t_auto_ef,
        duracion_minima_min=duracion_minima_min,
    )
    opciones_moto = calcular_opciones_duracion(
        usuario.municipio, t_moto_ef,
        duracion_minima_min=duracion_minima_min,
    )

    # Subcuadras (excluye "Zona Única" = default silencioso)
    subcuadras = (
        Subcuadra.objects
        .filter(municipio=usuario.municipio)
        .exclude(calle="Zona Única")
        .order_by("calle", "altura")
    )

    # IDs de vehículos con abono mensual activo
    _mes_actual = _date.today().replace(day=1)
    ids_con_abono = set(
        AbonoMensual.objects
        .filter(municipio=usuario.municipio, mes=_mes_actual)
        .values_list("vehiculo_id", flat=True)
    )

    # Últimos 3 vehículos distintos usados (para mostrarlos como "Recientes")
    ids_recientes = []
    visto = set()
    for est in (
        Estacionamiento.objects
        .filter(usuario=usuario)
        .order_by("-hora_inicio")
        .select_related("vehiculo")[:30]
    ):
        if est.vehiculo_id not in visto:
            visto.add(est.vehiculo_id)
            ids_recientes.append(est.vehiculo_id)
        if len(ids_recientes) >= 3:
            break
    ids_recientes_set = set(ids_recientes)

    vehiculos_qs = (
        Vehiculo.objects
        .filter(vehiculousuario__usuario=usuario)
        .distinct()
    )

    vehiculos_data = []
    for v in vehiculos_qs:
        vehiculos_data.append({
            "id":           v.id,
            "patente":      v.patente,
            "tipo":         v.tipo,
            "tipo_display": v.get_tipo_display(),
            "tiene_abono":  v.id in ids_con_abono,
            "exento":       bool(getattr(v, "exento_global", False)),
            "es_reciente":  v.id in ids_recientes_set,
        })
    # Recientes primero, luego el resto por patente
    vehiculos_data.sort(key=lambda v: (0 if v["es_reciente"] else 1, v["patente"]))

    saldo = obtener_saldo_conductor(usuario, usuario.municipio)

    return JsonResponse({
        "saldo":                  float(saldo),
        "dia_libre_hoy":          dia_libre,
        "fuera_de_horario":       fuera_de_horario,
        "mensaje_horario":        msg_horario,
        "tarifa_hora_auto":       float(t_auto_ef),
        "tarifa_hora_moto":       float(t_moto_ef),
        "descuento_pct":          descuento_pct,
        "vehiculos":              vehiculos_data,
        "opciones_duracion_auto": [
            {"horas": float(o["horas"]), "label": o["label"], "costo": float(o["costo"])}
            for o in opciones_auto
        ],
        "opciones_duracion_moto": [
            {"horas": float(o["horas"]), "label": o["label"], "costo": float(o["costo"])}
            for o in opciones_moto
        ],
        "subcuadras": [
            {
                "id":        s.id,
                "calle":     s.calle,
                "altura":    s.altura,
                "tipo_zona": s.tipo_zona,
                "entre":     s.entre_calles,
            }
            for s in subcuadras
        ],
        "geoloc_activa":          bool(
            usuario.municipio and getattr(usuario.municipio, "geoloc_conductor_activa", False)
        ),
        "selector_manual_activo": bool(
            not usuario.municipio
            or getattr(usuario.municipio, "selector_manual_conductor_activo", True)
        ),
        "url_subcuadra_cercana":  reverse("conductor_subcuadra_cercana"),
    })


@require_login
@require_POST
def api_conductor_estacionar(request):
    """
    POST /api/conductor/estacionar/

    Registra un estacionamiento para el conductor.
    Replica el flujo POST de estacionar_vehiculo() pero devuelve JSON en lugar
    de redirigir, para que el componente React pueda manejar el resultado.

    Body (JSON):
        vehiculo_id         — int
        horas               — float
        subcuadra_id        — int|null
        conductor_gps_lat   — str|null
        conductor_gps_lon   — str|null

    Respuesta OK:    { "ok": true, "redirect_url": "/...", "info_infraccion": {...}|null }
    Respuesta error: { "ok": false, "error_code": "...", "error": "...", "redirect_url": "..."|null }

    Por qué se setea request.session aquí:
    notif_infraccion_pendiente vive en la sesión de Django para que inicio_usuarios()
    pueda mostrarlo al volver. El endpoint de API es una vista Django normal, así que
    request.session funciona igual que en cualquier otra vista.
    """
    import json

    usuario = request.user

    try:
        body = json.loads(request.body)
    except Exception:
        return JsonResponse({"ok": False, "error": "JSON inválido."}, status=400)

    vehiculo_id       = body.get("vehiculo_id")
    horas             = body.get("horas")
    subcuadra_id      = body.get("subcuadra_id")
    conductor_gps_lat = body.get("conductor_gps_lat") or None
    conductor_gps_lon = body.get("conductor_gps_lon") or None

    # ── Resolver vehículo ────────────────────────────────────────────────────
    try:
        vehiculo = Vehiculo.objects.get(
            id=vehiculo_id, vehiculousuario__usuario=usuario
        )
    except Vehiculo.DoesNotExist:
        return JsonResponse(
            {"ok": False, "error": "Vehículo no encontrado.", "error_code": "vehiculo_no_encontrado"},
            status=400,
        )

    # Estacionamiento ya activo para este vehículo
    if Estacionamiento.objects.filter(vehiculo=vehiculo, estado="ACTIVO").exists():
        return JsonResponse(
            {"ok": False, "error": "El vehículo ya tiene un estacionamiento activo.", "error_code": "ya_activo"},
            status=400,
        )

    # ── Validación de horario ─────────────────────────────────────────────────
    # Los días libres omiten el chequeo de horario (igual que views_conductor).
    if not es_dia_libre_conductor(usuario.municipio):
        permitido, msg_horario = puede_estacionar_ahora(usuario.municipio)
        if not permitido:
            return JsonResponse(
                {"ok": False, "error": msg_horario or "Fuera de horario.", "error_code": "fuera_horario"},
                status=400,
            )

    # ── Validación de duración ────────────────────────────────────────────────
    tarifa_obj   = Tarifa.objects.filter(municipio=usuario.municipio).first()
    minutos_min  = tarifa_obj.duracion_minima_minutos if tarifa_obj else 30
    try:
        duracion         = Decimal(str(horas))
        duracion_min_h   = Decimal(str(round(minutos_min / 60, 4)))
        if duracion <= 0 or duracion < duracion_min_h:
            raise ValueError()
    except Exception:
        return JsonResponse(
            {"ok": False, "error": f"La duración mínima es {minutos_min} minutos.", "error_code": "duracion_invalida"},
            status=400,
        )

    # ── Resolver subcuadra ────────────────────────────────────────────────────
    if subcuadra_id:
        subcuadra = (
            Subcuadra.objects.filter(id=subcuadra_id, municipio=usuario.municipio).first()
            or get_subcuadra_default(usuario.municipio)
        )
    else:
        subcuadra = get_subcuadra_default(usuario.municipio)

    # ── Ejecutar use case ─────────────────────────────────────────────────────
    result = ejecutar_estacionamiento(
        usuario, vehiculo, subcuadra, duracion,
        gps_lat=conductor_gps_lat,
        gps_lon=conductor_gps_lon,
    )

    if not result["ok"]:
        error_code = result.get("error_code")
        if error_code == "abono_activo":
            return JsonResponse({
                "ok":         False,
                "error_code": "abono_activo",
                "error":      "Abono mensual activo. No necesitás registrar estacionamiento por hora.",
            }, status=400)
        return JsonResponse({
            "ok":           False,
            "error_code":   error_code or "saldo_insuficiente",
            "error":        "Saldo insuficiente. Cargá saldo para continuar.",
            "redirect_url": reverse(result["redirect"]),
        }, status=400)

    # ── Notificación de infracción detectada ──────────────────────────────────
    # Mismo comportamiento que views_conductor: si la infracción quedó pendiente,
    # se guarda en sesión para mostrarla al llegar a inicio_usuarios.
    info_inf = result.get("info_infraccion")
    respuesta_infraccion = None
    if info_inf:
        if info_inf["anulada"]:
            respuesta_infraccion = {
                "anulada": True,
                "mensaje": (
                    f"✅ Infracción anulada — pagaste dentro del período de gracia "
                    f"({info_inf['tolerancia_min']} min)."
                ),
            }
        else:
            # Guardar en sesión para que inicio_usuarios() la muestre al regresar
            request.session["notif_infraccion_pendiente"] = {
                "infraccion_id":        info_inf["infraccion_id"],
                "monto":                str(info_inf["monto"]),
                "tolerancia_min":       info_inf["tolerancia_min"],
                "hora_verificacion":    info_inf["hora_verificacion"].isoformat(),
                "hora_fin_gracia":      info_inf["hora_fin_gracia"].isoformat(),
                "hora_estacionamiento": info_inf["hora_estacionamiento"].isoformat(),
            }
            respuesta_infraccion = {
                "anulada": False,
                "monto":   str(info_inf["monto"]),
            }

    return JsonResponse({
        "ok":              True,
        "redirect_url":    reverse(result["redirect"]),
        "info_infraccion": respuesta_infraccion,
        "warnings":        result.get("warnings", []),
    })
