# app_estacionamiento/views_conductor.py
"""
Vistas del rol Conductor (ciudadano que estaciona).

Responsabilidades:
- Panel principal con estacionamiento activo
- Estacionar, renovar y finalizar un estacionamiento
- Ver historial de estacionamientos e infracciones
- Pagar infracciones propias con saldo
- Agregar y desvincular vehículos
- Solicitar verificación de identidad / exención
- Marcar notificaciones como leídas

No incluye cobros en efectivo ni gestión de caja (eso es vendedor).
No incluye gestión de municipio ni usuarios (eso es admin).
"""

from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .decorators import require_login, require_role
from .models import (
    AbonoMensual,
    Estacionamiento,
    Estado,
    Infraccion,
    MovimientoCaja,
    Notificacion,
    SolicitudVerificacion,
    Tarifa,
    Usuario,
    VerificacionInspector,
    Vehiculo,
    VehiculoUsuario,
)
from .use_cases.estacionar_vehiculo import ejecutar_estacionamiento
from .use_cases.finalizar_estacionamiento import ejecutar as finalizar_estacionamiento_uc
from .use_cases.pagar_infraccion import ejecutar as pagar_infraccion_uc
from .services.horarios import (
    calcular_opciones_duracion,
    cerrar_estacionamientos_vencidos_por_horario,
    puede_estacionar_ahora,
)
from .utils import get_subcuadra_default
from .views_auth import redirect_por_rol


# ─────────────────────────────────────────────────────────────────────────────
# Panel principal del conductor
# ─────────────────────────────────────────────────────────────────────────────

@require_role("inspector", "admin", "conductor", "vendedor")
def inicio_usuarios(request):
    """
    Panel de inicio del conductor.
    Muestra el estacionamiento activo, notificaciones y abonos del mes.
    También aplica auto-cierre si el tiempo venció o el horario del municipio terminó.
    """
    usuario = request.user

    estacionamiento_activo = Estacionamiento.objects.filter(
        usuario=usuario,
        estado="ACTIVO"
    ).order_by("-hora_inicio").first()

    # Auto-cierre: si el tiempo pago ya venció, finalizar automáticamente
    if estacionamiento_activo:
        expiracion = estacionamiento_activo.hora_inicio + timedelta(
            hours=estacionamiento_activo.duracion_horas
        )
        if timezone.now() >= expiracion:
            finalizar_estacionamiento_uc(estacionamiento_activo)
            estacionamiento_activo = None
            messages.info(
                request,
                "⏰ Tu estacionamiento finalizó automáticamente porque venció el tiempo pago."
            )

    # Auto-cierre por horario: si el municipio ya cerró, finalizar estacionamientos activos
    if usuario.municipio:
        cerrar_estacionamientos_vencidos_por_horario(usuario.municipio)

    # Notificaciones no leídas (ej: resultado de verificación de identidad)
    notificaciones_nuevas = Notificacion.objects.filter(
        destinatario=usuario, leida=False
    ).order_by("-fecha")

    # Estado de verificación: None si no existe solicitud
    solicitud_verificacion = getattr(usuario, "solicitud_verificacion", None)

    # Abonos mensuales activos del conductor para el mes en curso
    mes_actual = date.today().replace(day=1)
    abonos_activos = AbonoMensual.objects.filter(
        vehiculo__vehiculousuario__usuario=usuario,
        municipio=usuario.municipio,
        mes=mes_actual,
    ).select_related("vehiculo").distinct() if usuario.municipio else []

    return render(request, "usuarios/inicio_usuarios.html", {
        "usuario":               usuario,
        "estacionamiento_activo": estacionamiento_activo,
        "solicitud_verificacion": solicitud_verificacion,
        "notificaciones_nuevas": notificaciones_nuevas,
        "abonos_activos":        abonos_activos,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Notificaciones
# ─────────────────────────────────────────────────────────────────────────────

@require_login
def marcar_notificacion_leida(request, notif_id):
    """
    Marca una notificación como leída cuando el conductor presiona 'Entendido'.
    Solo acepta POST para evitar marcado accidental por GET.
    """
    if request.method == "POST":
        Notificacion.objects.filter(
            id=notif_id, destinatario=request.user
        ).update(leida=True)
    return redirect("inicio_usuarios")


# ─────────────────────────────────────────────────────────────────────────────
# Verificación de identidad y exenciones
# ─────────────────────────────────────────────────────────────────────────────

@require_role("conductor")
def solicitar_verificacion(request):
    """
    El conductor envía una solicitud de verificación de identidad y,
    opcionalmente, una solicitud de exención (discapacidad o frentista).

    Flujo de identidad:
      - Si la solicitud está aprobada → solo lectura, sin reenvío.
      - Si está pendiente → muestra estado.
      - Si está rechazada o no existe → puede enviar/reenviar.

    Flujo de exención (dentro de la misma solicitud):
      - Marcando "Solicito exención" aparecen: tipo, vehículo y documentos.
      - discapacidad  → documento_1 = CUD
      - frentista     → documento_1 = licencia, documento_2 = cédula de domicilio
    """
    usuario = request.user

    try:
        solicitud = usuario.solicitud_verificacion
    except SolicitudVerificacion.DoesNotExist:
        solicitud = None

    # Vehículos registrados del conductor para el selector de exención
    vehiculos_usuario = Vehiculo.objects.filter(
        vehiculousuario__usuario=usuario
    )

    if request.method == "POST":
        if usuario.es_verificado:
            messages.error(request, "Tu cuenta ya está verificada.")
            return redirect("inicio_usuarios")

        nombre   = request.POST.get("nombre", "").strip()
        apellido = request.POST.get("apellido", "").strip()
        dni      = request.POST.get("dni", "").strip()
        telefono = request.POST.get("telefono", "").strip()

        if not nombre or not apellido or not dni:
            messages.error(request, "Nombre, apellido y DNI son obligatorios.")
            return render(request, "usuarios/solicitar_verificacion.html", {
                "solicitud": solicitud,
                "vehiculos": vehiculos_usuario,
            })

        # ── Datos de exención (opcionales) ──────────────────────────────────
        solicita_exencion    = request.POST.get("solicita_exencion") == "on"
        tipo_exencion_sol    = request.POST.get("tipo_exencion_solicitado", "").strip()
        vehiculo_id          = request.POST.get("vehiculo_id", "").strip()

        vehiculo_obj = None
        if solicita_exencion and vehiculo_id:
            vehiculo_obj = Vehiculo.objects.filter(
                id=vehiculo_id,
                vehiculousuario__usuario=usuario
            ).first()

        # Validar documentos según tipo de exención
        doc1 = request.FILES.get("documento_1")
        doc2 = request.FILES.get("documento_2")

        if solicita_exencion:
            if not tipo_exencion_sol:
                messages.error(request, "Seleccioná el tipo de exención.")
                return render(request, "usuarios/solicitar_verificacion.html", {
                    "solicitud": solicitud, "vehiculos": vehiculos_usuario,
                })
            if not vehiculo_obj:
                messages.error(request, "Seleccioná el vehículo para la exención.")
                return render(request, "usuarios/solicitar_verificacion.html", {
                    "solicitud": solicitud, "vehiculos": vehiculos_usuario,
                })
            if not doc1 and not (solicitud and solicitud.documento_1):
                messages.error(request, "Adjuntá el documento principal requerido.")
                return render(request, "usuarios/solicitar_verificacion.html", {
                    "solicitud": solicitud, "vehiculos": vehiculos_usuario,
                })
            if tipo_exencion_sol == "vecino_frentista" and not doc2 and not (solicitud and solicitud.documento_2):
                messages.error(request, "La exención de frentista requiere la cédula de domicilio.")
                return render(request, "usuarios/solicitar_verificacion.html", {
                    "solicitud": solicitud, "vehiculos": vehiculos_usuario,
                })

        # ── Crear o actualizar la solicitud ─────────────────────────────────
        if solicitud:
            solicitud.nombre    = nombre
            solicitud.apellido  = apellido
            solicitud.dni       = dni
            solicitud.telefono  = telefono
            solicitud.estado    = "pendiente"
            solicitud.notas_admin = ""

            solicitud.solicita_exencion          = solicita_exencion
            solicitud.tipo_exencion_solicitado   = tipo_exencion_sol if solicita_exencion else ""
            solicitud.vehiculo                   = vehiculo_obj if solicita_exencion else None

            if solicita_exencion:
                solicitud.estado_exencion         = "pendiente"
                solicitud.notas_exencion_admin    = ""
                if doc1:
                    solicitud.documento_1 = doc1
                if doc2:
                    solicitud.documento_2 = doc2
            else:
                solicitud.estado_exencion = ""
                solicitud.documento_1 = None
                solicitud.documento_2 = None

            solicitud.save()
        else:
            kwargs = dict(
                usuario=usuario,
                nombre=nombre,
                apellido=apellido,
                dni=dni,
                telefono=telefono,
                solicita_exencion=solicita_exencion,
            )
            if solicita_exencion:
                kwargs["tipo_exencion_solicitado"] = tipo_exencion_sol
                kwargs["vehiculo"]                 = vehiculo_obj
                kwargs["estado_exencion"]          = "pendiente"
                if doc1:
                    kwargs["documento_1"] = doc1
                if doc2:
                    kwargs["documento_2"] = doc2

            solicitud = SolicitudVerificacion.objects.create(**kwargs)

        messages.success(request, "¡Solicitud enviada! El admin la revisará a la brevedad.")
        return redirect("inicio_usuarios")

    return render(request, "usuarios/solicitar_verificacion.html", {
        "solicitud": solicitud,
        "vehiculos": vehiculos_usuario,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Infracciones propias del conductor
# ─────────────────────────────────────────────────────────────────────────────

@require_login
def mis_infracciones(request):
    """
    El conductor ve las infracciones asociadas a sus vehículos.
    No conductores (admin, inspector, vendedor) son redirigidos a su panel.
    """
    usuario = request.user

    # Solo conductores tienen infracciones propias.
    if not usuario.es_conductor:
        messages.info(request, "Esta sección es solo para conductores.")
        return redirect_por_rol(usuario)

    if not usuario.es_verificado and not usuario.vehiculos.exists():
        messages.info(
            request,
            "No tenés vehículos registrados. "
            "Agregá tu vehículo o verificá tu cuenta para ver tus infracciones."
        )
        return redirect("solicitar_verificacion")

    infracciones = (
        Infraccion.objects
        .filter(vehiculo__vehiculousuario__usuario=usuario)
        .distinct()
        .order_by("-creado_en")
    )

    return render(request, "usuarios/historial_infracciones.html", {
        "infracciones":    infracciones,
        "saldo_usuario":   usuario.saldo,
        "tiene_pendientes": infracciones.filter(estado="pendiente").exists(),
    })


@require_login
def pagar_infraccion(request, infraccion_id):
    """
    El conductor paga una infracción propia usando su saldo digital.
    Delega la lógica al use case pagar_infraccion_uc.
    Solo acepta POST. La infracción debe estar vinculada a una patente del conductor.
    """
    infraccion = get_object_or_404(
        Infraccion,
        id=infraccion_id,
        municipio=request.user.municipio,
        vehiculo__vehiculousuario__usuario=request.user,  # seguridad: solo sus patentes
    )
    if request.method != "POST":
        return redirect("mis_infracciones")
    try:
        pagar_infraccion_uc(request.user, infraccion)
        messages.success(request, f"✅ Infracción #{infraccion.id} pagada con tu saldo.")
    except Exception as e:
        messages.error(request, str(e))
    return redirect("mis_infracciones")


# ─────────────────────────────────────────────────────────────────────────────
# Vehículos del conductor
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def agregar_vehiculo(request):
    """
    El conductor agrega un vehículo a su cuenta.
    Si la patente ya existe en el sistema la vincula; si no, la crea.
    Redirige a estacionar para que pueda usarlo de inmediato.
    """
    if request.method == "POST":
        patente = request.POST.get("patente", "").strip().upper()
        tipo    = request.POST.get("tipo", "auto")

        if tipo not in ("auto", "moto"):
            tipo = "auto"

        if not patente:
            return redirect("inicio")

        vehiculo, creado = Vehiculo.objects.get_or_create(patente=patente)

        if creado:
            vehiculo.tipo = tipo
            vehiculo.save(update_fields=["tipo"])

        VehiculoUsuario.objects.get_or_create(
            usuario=request.user,
            vehiculo=vehiculo
        )

        return redirect(
            reverse("usuarios_estacionar_vehiculo")
            + f"?patente={vehiculo.patente}"
        )

    return render(request, "usuarios/agregar_vehiculo.html")


@require_login
def eliminar_vehiculo(request, vehiculo_id):
    """
    El conductor desvincula un vehículo de su cuenta.
    No elimina el vehículo del sistema, solo la relación VehiculoUsuario.
    """
    if request.method == "POST":
        VehiculoUsuario.objects.filter(
            usuario=request.user,
            vehiculo_id=vehiculo_id
        ).delete()
    return redirect("usuarios_estacionar_vehiculo")


# ─────────────────────────────────────────────────────────────────────────────
# Estacionamiento del conductor
# ─────────────────────────────────────────────────────────────────────────────

@require_role("conductor")
def estacionar_vehiculo(request):
    """
    El conductor estaciona su vehículo con saldo digital.

    Flujo POST:
    1. Recibe patente (o vehiculo_id) + duración
    2. Valida horario del municipio
    3. Delega al use case ejecutar_estacionamiento (cobra saldo, crea Estacionamiento)
    4. Muestra aviso si el vehículo fue escaneado recientemente por un inspector

    Flujo GET:
    - Muestra dropdown de vehículos del conductor y opciones de duración según tarifa
    """
    from .models import Tarifa

    usuario  = request.user
    warning  = None
    vehiculos = Vehiculo.objects.filter(
        vehiculousuario__usuario=usuario
    ).distinct()

    if request.method == "POST":
        patente    = (request.POST.get("patente") or "").strip().upper()
        vehiculo_id = request.POST.get("vehiculo_id")
        duracion   = request.POST.get("duracion") or request.POST.get("horas")

        # ── Resolver vehículo ────────────────────────────────────────────────
        if vehiculo_id:
            vehiculo = get_object_or_404(
                Vehiculo,
                id=vehiculo_id,
                vehiculousuario__usuario=usuario,
            )
        else:
            if not patente:
                return render(request, "usuarios/estacionar_vehiculo.html", {
                    "error": "Debe ingresar una patente",
                    "vehiculos": vehiculos,
                    "usuario": usuario,
                })
            vehiculo, _ = Vehiculo.objects.get_or_create(patente=patente)

        if not vehiculo.municipio:
            vehiculo.municipio = usuario.municipio
            vehiculo.save()

        # Asegurar relación conductor ↔ vehículo
        VehiculoUsuario.objects.get_or_create(
            usuario=usuario,
            vehiculo=vehiculo,
            defaults={"es_propietario": True, "verificado": False},
        )

        # ── Validaciones ─────────────────────────────────────────────────────
        if vehiculo.exento_global:
            return render(request, "inspectores/verificar_vehiculo.html", {
                "resultado": {
                    "patente": vehiculo.patente,
                    "estado": "Exento TOTAL",
                    "estacionamiento_activo": True,
                }
            })

        if Estacionamiento.objects.filter(vehiculo=vehiculo, estado="ACTIVO").exists():
            return render(request, "usuarios/estacionar_vehiculo.html", {
                "error":    "El vehículo ya tiene un estacionamiento activo.",
                "warning":  warning,
                "vehiculos": vehiculos,
                "usuario":  usuario,
            })

        permitido, msg_horario = puede_estacionar_ahora(usuario.municipio)
        if not permitido:
            return render(request, "usuarios/estacionar_vehiculo.html", {
                "error":    msg_horario,
                "warning":  warning,
                "vehiculos": vehiculos,
                "usuario":  usuario,
            })

        # ── Duración ─────────────────────────────────────────────────────────
        try:
            duracion = Decimal(duracion)
            if duracion <= 0:
                raise ValueError()
        except Exception:
            return render(request, "usuarios/estacionar_vehiculo.html", {
                "error":    "Duración inválida",
                "warning":  warning,
                "vehiculos": vehiculos,
                "usuario":  usuario,
            })

        subcuadra = get_subcuadra_default(usuario.municipio)
        result    = ejecutar_estacionamiento(usuario, vehiculo, subcuadra, duracion)

        for w in result.get("warnings", []):
            messages.warning(request, w)

        if not result["ok"]:
            return redirect(reverse(result["redirect"]))

        # Aviso si el inspector escaneó el vehículo recientemente (dentro de 15 min)
        escaneado_recientemente = VerificacionInspector.objects.filter(
            vehiculo=vehiculo,
            fecha__gte=timezone.now() - timedelta(minutes=15),
        ).exists()
        if escaneado_recientemente:
            messages.info(
                request,
                "⚠️ Tu vehículo fue escaneado por un inspector. "
                "Como pagaste a tiempo, la infracción quedó cancelada."
            )

        return redirect(reverse(result["redirect"]))

    # ── GET ──────────────────────────────────────────────────────────────────
    tarifa_obj       = Tarifa.objects.filter(municipio=usuario.municipio).first()
    tarifa_hora_auto = tarifa_obj.precio_por_hora if tarifa_obj else 100
    tarifa_hora_moto = (
        tarifa_obj.precio_por_hora_moto
        if tarifa_obj and tarifa_obj.precio_por_hora_moto
        else tarifa_hora_auto
    )

    patente_preseleccionada = request.GET.get("patente", "").strip().upper()
    opciones_duracion = calcular_opciones_duracion(usuario.municipio, tarifa_hora_auto)

    return render(request, "usuarios/estacionar_vehiculo.html", {
        "vehiculos":             vehiculos,
        "usuario":               usuario,
        "tarifa_hora":           tarifa_hora_auto,
        "tarifa_hora_auto":      tarifa_hora_auto,
        "tarifa_hora_moto":      tarifa_hora_moto,
        "patente_preseleccionada": patente_preseleccionada,
        "opciones_duracion":     opciones_duracion,
    })


@require_role("conductor")
def historial_estacionamientos(request):
    """Lista de todos los estacionamientos del conductor, ordenados por fecha desc."""
    usuario = request.user
    estacionamientos = (
        Estacionamiento.objects
        .filter(usuario=usuario)
        .order_by("-hora_inicio")
    )
    return render(request, "usuarios/historial_estacionamientos.html", {
        "estacionamientos": estacionamientos,
    })


@require_role("conductor")
def renovar_estacionamiento(request, est_id):
    """
    El conductor extiende las horas de su estacionamiento activo.
    Cobra la diferencia de saldo según la tarifa vigente.
    Las opciones de extensión están limitadas al horario de cierre del municipio.
    """
    usuario        = request.user
    estacionamiento = get_object_or_404(
        Estacionamiento,
        id=est_id,
        usuario=usuario,
        estado="ACTIVO",
    )

    tarifa_obj  = Tarifa.objects.filter(municipio=usuario.municipio).first()
    tarifa_hora = tarifa_obj.precio_por_hora if tarifa_obj else Decimal("100")
    error       = None

    if request.method == "POST":
        try:
            horas_extra = Decimal(request.POST.get("horas_extra", "0"))
            if horas_extra <= 0:
                raise ValueError()
        except Exception:
            error = "Ingresá una cantidad de horas válida."
        else:
            costo_extra = horas_extra * tarifa_hora

            if usuario.saldo < costo_extra:
                error = f"Saldo insuficiente. Necesitás ${costo_extra:.2f} y tenés ${usuario.saldo:.2f}."
            else:
                with transaction.atomic():
                    usuario_db = Usuario.objects.select_for_update().get(id=usuario.id)
                    if usuario_db.saldo < costo_extra:
                        error = "Saldo insuficiente."
                    else:
                        estacionamiento.duracion_horas = estacionamiento.duracion_horas + int(horas_extra)
                        estacionamiento.save(update_fields=["duracion_horas"])

                        usuario_db.saldo -= costo_extra
                        usuario_db.save(update_fields=["saldo"])

                        MovimientoCaja.objects.create(
                            usuario=usuario_db,
                            monto=costo_extra,
                            tipo="egreso",
                            descripcion=f"Renovación {horas_extra:.0f}h — {estacionamiento.vehiculo.patente}",
                        )

                        messages.success(
                            request,
                            f"✅ Estacionamiento extendido {horas_extra:.0f}h más. "
                            f"Se descontaron ${costo_extra:.2f} de tu saldo."
                        )
                        return redirect("inicio_usuarios")

    opciones_duracion = calcular_opciones_duracion(
        municipio=usuario.municipio,
        tarifa_hora=tarifa_hora,
        hora_inicio_est=estacionamiento.hora_inicio,
        duracion_actual_h=float(estacionamiento.duracion_horas),
    )

    return render(request, "usuarios/renovar_estacionamiento.html", {
        "estacionamiento":  estacionamiento,
        "tarifa_hora":      tarifa_hora,
        "saldo":            usuario.saldo,
        "error":            error,
        "opciones_duracion": opciones_duracion,
    })


@require_role("conductor")
def finalizar_estacionamiento(request, estacionamiento_id):
    """
    El conductor finaliza su estacionamiento anticipadamente.
    GET → pantalla de confirmación con costo estimado.
    POST → ejecuta el use case y redirige al historial.
    """
    estacionamiento = get_object_or_404(
        Estacionamiento,
        id=estacionamiento_id,
        usuario=request.user,
    )

    if estacionamiento.estado != Estado.ACTIVO:
        return redirect("usuarios_historial_estacionamientos")

    if request.method != "POST":
        return render(request, "usuarios/finalizar_estacionamiento.html", {
            "estacionamiento": estacionamiento,
            "duracion_horas":  estacionamiento.duracion_horas,
            "costo_estimado":  estacionamiento.costo_base,
            "usuario":         request.user,
        })

    resultado = finalizar_estacionamiento_uc(estacionamiento)

    if resultado["ok"]:
        messages.success(request, f"Estacionamiento finalizado. Costo: ${resultado['costo']}")
    else:
        messages.error(request, resultado.get("error", "Error al finalizar"))

    return redirect("usuarios_historial_estacionamientos")


# ─────────────────────────────────────────────────────────────────────────────
# Utilidades de desarrollo
# ─────────────────────────────────────────────────────────────────────────────

@require_login
def simular_pago(request, infraccion_id):
    """
    Solo disponible en DEBUG=True. Marca una infracción como pagada sin pasar
    por MercadoPago. Devuelve 404 en producción para evitar bypasses.
    """
    if not settings.DEBUG:
        from django.http import Http404
        raise Http404("No disponible en producción.")

    infraccion = get_object_or_404(Infraccion, id=infraccion_id)
    infraccion.estado = "pagada"
    infraccion.save()
    return redirect("inspectores_ticket", infraccion.id)
