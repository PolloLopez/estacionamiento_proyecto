# app_estacionamiento/use_cases/estacionar_vehiculo.py
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from app_estacionamiento.factories import EstacionamientoFactory
from app_estacionamiento.models import Infraccion, Usuario, VehiculoUsuario, Tarifa
from app_estacionamiento.domain.vehiculo_policy import VehiculoPolicy
from app_estacionamiento.domain.saldo_policy import SaldoPolicy

from app_estacionamiento.services.horarios import obtener_tarifa_hora, es_dia_libre_conductor
from app_estacionamiento.services.saldo import debitar_saldo_conductor
from app_estacionamiento.services.infracciones import calcular_estado_tolerancia
from app_estacionamiento.services.reintegro import aplicar_reintegro
from app_estacionamiento.services.descuentos_verificados import aplicar_descuento_conductor

REDIRECT_OK        = "inicio_usuarios"
REDIRECT_SIN_SALDO = "mp_iniciar_carga"


def ejecutar_estacionamiento(usuario, vehiculo, subcuadra, duracion, gps_lat=None, gps_lon=None):
    """
    Registra un estacionamiento para el conductor.

    Flujo:
    1. Valida duracion y saldo (optimista sin lock).
    2. Dentro de transaction.atomic() con select_for_update:
       a. Revalida saldo (con lock para evitar race condition).
       b. Chequea si el vehiculo tiene infraccion pendiente:
          - Dentro de tolerancia → anula la infraccion sin cobrar.
          - Fuera de tolerancia  → deja la infraccion pendiente,
            retorna info para mostrar notificacion al conductor.
       c. Crea el Estacionamiento y debita el saldo.

    Retorna dict con:
      - ok         (bool)
      - redirect   (str)  — nombre de URL
      - warnings   (list) — avisos de VehiculoPolicy
      - error_code (str|None) — motivo del rechazo si ok=False
      - info_infraccion — None, o dict con datos de la infraccion detectada
    """
    from datetime import date
    from app_estacionamiento.models import AbonoMensual

    try:
        duracion = Decimal(duracion)
        if duracion <= 0:
            raise ValueError()
    except Exception:
        return {
            "ok": False,
            "redirect": "inicio",
            "warnings": [],
            "error_code": None,
            "info_infraccion": None,
            "info_reintegro":  None,
        }

    # Bloqueo de abono mensual activo:
    # Si el vehículo tiene abono para este mes y municipio, el conductor
    # ya pagó por estacionar libremente — no se puede cobrar por hora encima.
    # El inspector ve "abono activo" al verificar, así que el registro
    # por hora es redundante y representaría un doble cobro injusto.
    if usuario.municipio:
        mes_actual = date.today().replace(day=1)
        tiene_abono_activo = AbonoMensual.objects.filter(
            vehiculo=vehiculo,
            municipio=usuario.municipio,
            mes=mes_actual,
        ).exists()

        if tiene_abono_activo:
            return {
                "ok": False,
                "redirect": "inicio_usuarios",
                "warnings": [],
                "error_code": "abono_activo",
                "info_infraccion": None,
                "info_reintegro":  None,
            }

    # Zona libre o día sin horario: el estacionamiento se registra igualmente
    # (para que el inspector vea "PAGADO") pero el costo es $0.
    # Esto es la red de seguridad del backend: el frontend ya oculta el formulario
    # de pago, pero si alguien enviara el POST igual, no se le cobra.
    zona_libre = subcuadra and getattr(subcuadra, "tipo_zona", None) == "libre"
    # es_dia_libre_conductor cubre tanto días sin horario como DiaEspecial sin cobro
    dia_libre  = usuario.municipio and es_dia_libre_conductor(usuario.municipio)

    if zona_libre or dia_libre:
        tarifa_hora = Decimal("0")
        costo_base  = Decimal("0")
        resultado_descuento = {"costo_final": Decimal("0"), "descuento_pct": Decimal("0"), "motivo": ""}
        costo = Decimal("0")
    else:
        tarifa_obj  = Tarifa.objects.filter(municipio=usuario.municipio).first()
        # subcuadra.precio_por_hora_custom tiene prioridad sobre la tarifa general
        tarifa_hora = obtener_tarifa_hora(tarifa_obj, vehiculo, subcuadra=subcuadra)
        costo_base  = duracion * tarifa_hora

        # Descuento para conductores verificados (configurado por el superadmin).
        # Se calcula antes del lock — es solo aritmética, sin race condition posible.
        resultado_descuento = aplicar_descuento_conductor(costo_base, usuario, usuario.municipio)
        costo = resultado_descuento["costo_final"]

    relaciones = VehiculoUsuario.objects.filter(vehiculo=vehiculo)
    warnings   = VehiculoPolicy.generar_warnings(usuario, vehiculo, relaciones)

    municipio = usuario.municipio
    if not SaldoPolicy.tiene_saldo(usuario, costo, municipio=municipio):
        return {
            "ok": False,
            "redirect": REDIRECT_SIN_SALDO,
            "warnings": warnings,
            "info_infraccion": None,
            "info_reintegro":  None,
        }

    with transaction.atomic():

        usuario_db = Usuario.objects.select_for_update().get(id=usuario.id)

        if not SaldoPolicy.tiene_saldo(usuario_db, costo, municipio=municipio):
            return {
                "ok": False,
                "redirect": REDIRECT_SIN_SALDO,
                "warnings": warnings,
                "info_infraccion": None,
                "info_reintegro":  None,
            }

        # ── Chequeo de infraccion pendiente ───────────────────────────────────
        # Si el vehiculo tiene una infraccion pendiente en este municipio,
        # aplicar la logica de tolerancia de gracia.
        ahora = timezone.now()
        info_infraccion = None

        if usuario.municipio:
            infraccion_pendiente = Infraccion.objects.filter(
                vehiculo=vehiculo,
                municipio=usuario.municipio,
                estado="pendiente",
            ).order_by("-creado_en").first()

            if infraccion_pendiente:
                estado_tol = calcular_estado_tolerancia(
                    infraccion_pendiente,
                    usuario.municipio,
                    ahora=ahora,
                )

                if estado_tol["dentro_tolerancia"]:
                    # Anular la infraccion sin cobrar
                    infraccion_pendiente.estado     = "anulada"
                    infraccion_pendiente.fecha_pago = ahora
                    infraccion_pendiente.save()
                    info_infraccion = {
                        "anulada":           True,
                        "tolerancia_min":    estado_tol["tolerancia_min"],
                        "hora_verificacion": estado_tol["hora_verificacion"],
                        "hora_fin_gracia":   estado_tol["hora_fin_gracia"],
                    }
                else:
                    # Dejar pendiente — conductor puede pagarla desde la app
                    info_infraccion = {
                        "anulada":              False,
                        "infraccion_id":        infraccion_pendiente.id,
                        "monto":                infraccion_pendiente.monto,
                        "tolerancia_min":       estado_tol["tolerancia_min"],
                        "hora_verificacion":    estado_tol["hora_verificacion"],
                        "hora_fin_gracia":      estado_tol["hora_fin_gracia"],
                        "hora_estacionamiento": ahora,
                    }

        estacionamiento = EstacionamientoFactory.crear(
            usuario=usuario_db,
            vehiculo=vehiculo,
            subcuadra=subcuadra,
            duracion=duracion,
            costo_base=costo
        )

        # GPS del conductor: solo se guarda si el municipio tiene geoloc activa
        # y si el frontend envió coords válidas (el campo puede llegar vacío si el
        # navegador denegó permiso o el flag estaba desactivado al cargar la página).
        if gps_lat is not None and gps_lon is not None:
            from decimal import InvalidOperation
            try:
                estacionamiento.gps_lat = Decimal(str(gps_lat))
                estacionamiento.gps_lon = Decimal(str(gps_lon))
                estacionamiento.save(update_fields=["gps_lat", "gps_lon"])
            except (InvalidOperation, ValueError):
                pass  # coords inválidas: se ignoran silenciosamente

        # debitar_saldo_conductor descuenta saldo y registra el egreso en caja.
        # usuario_db ya esta bloqueado con select_for_update(), no abre nueva transaccion.
        debitar_saldo_conductor(
            conductor=usuario_db,
            monto=costo,
            descripcion="Estacionamiento",
            municipio=municipio,
        )

        # ── Reintegro de vecinos (si el municipio tiene el módulo activo) ───────
        # Se aplica después del débito para no interferir con el chequeo de saldo.
        # usuario_db ya está bloqueado; aplicar_reintegro opera sobre el mismo objeto.
        info_reintegro = None
        if usuario.municipio:
            resultado = aplicar_reintegro(
                conductor=usuario_db,
                municipio=usuario.municipio,
                estacionamiento=estacionamiento,
                tarifa_hora=tarifa_hora,
            )
            if resultado["reintegrado"]:
                info_reintegro = resultado

    return {
        "ok": True,
        "redirect": REDIRECT_OK,
        "warnings": warnings,
        "info_infraccion":  info_infraccion,
        "info_reintegro":   info_reintegro,
        "descuento_pct":    resultado_descuento["descuento_pct"],
        "descuento_motivo": resultado_descuento["motivo"],
    }
