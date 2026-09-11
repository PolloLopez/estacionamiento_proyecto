# app_estacionamiento/views_superadmin.py
"""
Vistas del rol Superadmin.

El superadmin es global: no pertenece a ningún municipio.
Puede ver y gestionar todos los municipios del sistema.

Responsabilidades:
- Ver resumen de todos los municipios
- Crear y editar municipios
- Crear y gestionar admins de cualquier municipio
- Activar/desactivar módulos de pago por municipio
- Importar estacionamientos activos desde Excel del sistema anterior
"""

from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .decorators import require_role
from .views_admin import _error_password
from .models import CierreCaja, Estacionamiento, LiquidacionPlataforma, ModuloMunicipio, Municipio, Notificacion, PlantillaDocumento, Rendicion, Subcuadra, SugerenciaMejora, Usuario, Vehiculo
from .utils import sanitizar_patente


# ─────────────────────────────────────────────────────────────────────────────
# Panel principal
# ─────────────────────────────────────────────────────────────────────────────

@require_role("superadmin")
def panel_superadmin(request):
    """
    Vista de resumen global: lista todos los municipios con métricas básicas.
    """
    municipios = (
        Municipio.objects
        .annotate(
            cant_admins=Count(
                "usuario",
                filter=Q(usuario__es_admin=True, usuario__is_active=True)
            ),
            cant_modulos=Count(
                "modulos",
                filter=Q(modulos__activo=True)
            ),
        )
        .order_by("nombre")
    )

    total_municipios = municipios.count()
    total_admins = Usuario.objects.filter(es_admin=True, is_active=True).count()

    return render(request, "superadmin/panel.html", {
        "municipios":       municipios,
        "total_municipios": total_municipios,
        "total_admins":     total_admins,
        "modulos_choices":  ModuloMunicipio.MODULOS,
    })


@require_role("superadmin")
def auditoria_superadmin(request):
    """
    Vista financiera global: recaudado, rendido y pendiente de rendir por municipio.

    Métricas por municipio en el período seleccionado:
    - Recaudado:  suma de CierreCaja.monto_municipio (lo que le corresponde al municipio).
    - Rendido:    suma de Rendicion.total_neto con estado 'validada' por el tesorero.
    - Pendiente:  suma de CierreCaja.monto_municipio donde el cierre está certificado
                  pero aún no tiene rendición asociada.

    Nota: las queries son por municipio en un loop Python (N pequeño, ~10-20 municipios).
    """
    hoy = timezone.localtime().date()
    try:
        desde = date.fromisoformat(request.GET.get("desde", ""))
    except (ValueError, TypeError):
        desde = hoy.replace(day=1)
    try:
        hasta = date.fromisoformat(request.GET.get("hasta", ""))
    except (ValueError, TypeError):
        hasta = hoy

    municipios = Municipio.objects.filter(activo=True).order_by("nombre")

    datos = []
    for m in municipios:
        # Total que el municipio recaudó (neto de comisiones de vendedores)
        recaudado = (
            CierreCaja.objects.filter(
                usuario__municipio=m,
                fecha_cierre__date__gte=desde,
                fecha_cierre__date__lte=hasta,
            ).aggregate(total=Sum("monto_municipio"))["total"] or 0
        )
        # Total validado por el tesorero en el período
        rendido = (
            Rendicion.objects.filter(
                municipio=m,
                estado="validada",
                creado_en__date__gte=desde,
                creado_en__date__lte=hasta,
            ).aggregate(total=Sum("total_neto"))["total"] or 0
        )
        # Certificado por el admin pero aún sin rendición generada
        pendiente_rendir = (
            CierreCaja.objects.filter(
                usuario__municipio=m,
                certificado=True,
                rendicion__isnull=True,
                fecha_cierre__date__gte=desde,
                fecha_cierre__date__lte=hasta,
            ).aggregate(total=Sum("monto_municipio"))["total"] or 0
        )
        datos.append({
            "municipio": m,
            "recaudado": recaudado,
            "rendido": rendido,
            "pendiente_rendir": pendiente_rendir,
        })

    total_recaudado   = sum(d["recaudado"]       for d in datos)
    total_rendido     = sum(d["rendido"]         for d in datos)
    total_pendiente   = sum(d["pendiente_rendir"] for d in datos)

    return render(request, "superadmin/auditoria.html", {
        "datos":            datos,
        "desde":            desde,
        "hasta":            hasta,
        "hoy":              hoy,
        "total_recaudado":  total_recaudado,
        "total_rendido":    total_rendido,
        "total_pendiente":  total_pendiente,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Gestión de municipios
# ─────────────────────────────────────────────────────────────────────────────

@require_role("superadmin")
def crear_municipio(request):
    """Crea un nuevo municipio."""
    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        if not nombre:
            messages.error(request, "El nombre del municipio es obligatorio.")
            return redirect("crear_municipio")

        if Municipio.objects.filter(nombre__iexact=nombre).exists():
            messages.error(request, f"Ya existe un municipio con el nombre '{nombre}'.")
            return redirect("crear_municipio")

        municipio = Municipio.objects.create(
            nombre=nombre,
            activo=True,
        )
        messages.success(request, f"Municipio '{municipio.nombre}' creado.")
        return redirect("panel_superadmin")

    return render(request, "superadmin/crear_municipio.html")


@require_role("superadmin")
def editar_municipio(request, municipio_id):
    """Edita la configuración de un municipio existente."""
    municipio = get_object_or_404(Municipio, id=municipio_id)

    if request.method == "POST":
        accion = request.POST.get("accion", "")

        if accion == "toggle_activo":
            municipio.activo = not municipio.activo
            municipio.save(update_fields=["activo"])
            estado = "activado" if municipio.activo else "desactivado"
            messages.success(request, f"Municipio {estado}.")
            return redirect("panel_superadmin")

        if accion == "generar_token_tv":
            import secrets
            municipio.token_tv = secrets.token_urlsafe(32)
            municipio.save(update_fields=["token_tv"])
            messages.success(request, "Token TV generado. Guardá la URL antes de cerrar.")
            return redirect("editar_municipio", municipio_id=municipio.id)

        if accion == "limpiar_datos_prueba":
            # Verificación con texto de confirmación: "CONFIRMAR+NOMBREMUNICIPIO"
            confirmacion = request.POST.get("confirmacion_texto", "").strip()
            esperado = f"CONFIRMAR+{municipio.nombre.upper()}"
            if confirmacion.upper() != esperado:
                messages.error(
                    request,
                    f"Texto incorrecto. Escribí exactamente: {esperado}",
                )
                return redirect("editar_municipio", municipio_id=municipio.id)

            from .models import (
                AbonoMensual, Impugnacion, Infraccion,
                PagoPublico, Reintegro, TransferenciaSaldo,
            )

            # IDs de conductores antes de borrarlos (para el mensaje final)
            conductores_ids = list(
                Usuario.objects.filter(
                    municipio=municipio, es_conductor=True
                ).values_list("id", flat=True)
            )

            # El orden importa: primero se borran los que tienen PROTECT hacia
            # Infraccion, Estacionamiento o Usuario (conductor).
            with transaction.atomic():
                # 1. Impugnaciones (PROTECT conductor → va primero)
                Impugnacion.objects.filter(municipio=municipio).delete()
                # 2. Reintegros (PROTECT conductor → va primero)
                Reintegro.objects.filter(municipio=municipio).delete()
                # 3. Transferencias (PROTECT emisor/receptor)
                TransferenciaSaldo.objects.filter(
                    emisor__municipio=municipio
                ).delete()
                # 4. Abonos mensuales
                AbonoMensual.objects.filter(municipio=municipio).delete()
                # 5. Infracciones (PROTECT vehiculo — se libera aquí)
                Infraccion.objects.filter(municipio=municipio).delete()
                # 6. Estacionamientos (PROTECT usuario conductor — se libera aquí)
                Estacionamiento.objects.filter(
                    subcuadra__municipio=municipio
                ).delete()
                # 7. PagoPublico del municipio (FKs ya son SET_NULL — limpieza final)
                PagoPublico.objects.filter(municipio=municipio).delete()
                # 8. Conductores: CASCADE en SolicitudVerificacion, Notificacion,
                #    VehiculoUsuario — ya no hay PROTECT activo sobre ellos.
                Usuario.objects.filter(id__in=conductores_ids).delete()

            messages.success(
                request,
                f"Datos de prueba eliminados: {len(conductores_ids)} conductor/es, "
                f"estacionamientos, infracciones, abonos, transferencias e impugnaciones "
                f"de {municipio.nombre}.",
            )
            return redirect("editar_municipio", municipio_id=municipio.id)

        # ── Helpers numéricos (ignoran string vacío) ─────────────────────────
        def _decimal(nombre, fallback):
            val = request.POST.get(nombre, "").strip()
            if not val:
                return fallback
            try:
                return Decimal(val)
            except (InvalidOperation, TypeError):
                return fallback

        def _entero(nombre, fallback):
            val = request.POST.get(nombre, "").strip()
            if not val:
                return fallback
            try:
                return int(val)
            except (ValueError, TypeError):
                return fallback

        # ── Sección: datos generales ──────────────────────────────────────
        if accion in ("guardar_general", ""):
            municipio.nombre                     = request.POST.get("nombre", municipio.nombre).strip()
            municipio.nombre_sistema             = request.POST.get("nombre_sistema", "").strip()
            municipio.monto_minimo_carga         = _entero("monto_minimo_carga",         municipio.monto_minimo_carga)
            municipio.monto_maximo_carga         = _entero("monto_maximo_carga",         municipio.monto_maximo_carga)
            municipio.minutos_entre_infracciones  = _entero("minutos_entre_infracciones",  municipio.minutos_entre_infracciones)
            municipio.segundos_pausa_doble_copia  = _entero("segundos_pausa_doble_copia",  municipio.segundos_pausa_doble_copia)
            municipio.activo                     = request.POST.get("activo") == "on"
            municipio.reintegro_minutos          = _entero("reintegro_minutos",          municipio.reintegro_minutos)
            municipio.reintegro_max_por_dia      = _entero("reintegro_max_por_dia",      municipio.reintegro_max_por_dia)
            alcance = request.POST.get("reintegro_alcance", "").strip()
            if alcance in ("todos", "residentes"):
                municipio.reintegro_alcance = alcance
            municipio.save()
            messages.success(request, "Configuración general guardada.")
            return redirect("editar_municipio", municipio_id=municipio.id)

        # ── Sección: facturación de la plataforma ────────────────────────
        if accion == "guardar_facturacion":
            municipio.cuota_mantenimiento_mensual = _decimal(
                "cuota_mantenimiento_mensual", municipio.cuota_mantenimiento_mensual
            )
            municipio.porcentaje_plataforma = _decimal(
                "porcentaje_plataforma", municipio.porcentaje_plataforma
            )
            dia = _entero("dia_cierre_liquidacion", municipio.dia_cierre_liquidacion)
            if 1 <= dia <= 28:
                municipio.dia_cierre_liquidacion = dia
            concepto = request.POST.get("concepto_recaudacion", "").strip()
            if concepto in ("cierre_caja", "rendiciones", "manual"):
                municipio.concepto_recaudacion = concepto
            municipio.save()
            messages.success(request, "Facturación guardada.")
            return redirect("editar_municipio", municipio_id=municipio.id)

        # ── Sección: información institucional ───────────────────────────
        if accion == "guardar_institucional":
            municipio.leyenda_horarios = request.POST.get("leyenda_horarios", "").strip()
            municipio.texto_ordenanza  = request.POST.get("texto_ordenanza", "").strip()
            municipio.save()
            messages.success(request, "Información institucional guardada.")
            return redirect("editar_municipio", municipio_id=municipio.id)

        # ── Sección: branding / identidad visual ─────────────────────────
        if accion == "guardar_branding":
            color_primario   = request.POST.get("color_primario_hex", "").strip()
            color_secundario = request.POST.get("color_secundario_hex", "").strip()
            color_acento     = request.POST.get("color_acento_hex", "").strip()
            if color_primario.startswith("#") and len(color_primario) in (4, 7):
                municipio.color_primario = color_primario
            if color_secundario.startswith("#") and len(color_secundario) in (4, 7):
                municipio.color_secundario = color_secundario
            if color_acento.startswith("#") and len(color_acento) in (4, 7):
                municipio.color_acento = color_acento
            if request.POST.get("borrar_logo") and municipio.logo:
                municipio.logo.delete(save=False)
                municipio.logo = None
            if "logo" in request.FILES:
                municipio.logo = request.FILES["logo"]
            if request.POST.get("borrar_icono_app") and municipio.icono_app:
                municipio.icono_app.delete(save=False)
                municipio.icono_app = None
            if "icono_app" in request.FILES:
                municipio.icono_app = request.FILES["icono_app"]
            municipio.save()
            messages.success(request, "Identidad visual guardada.")
            return redirect("editar_municipio", municipio_id=municipio.id)

    admins    = Usuario.objects.filter(municipio=municipio, es_admin=True).order_by("-is_active", "correo")
    tesoreros = Usuario.objects.filter(municipio=municipio, es_tesorero=True).order_by("-is_active", "correo")
    modulos_activos = {m.modulo: m for m in ModuloMunicipio.objects.filter(municipio=municipio)}

    # Descripción de cada módulo
    descripciones_modulos = {
        "ocupacion_tiempo_real":     "Mapa o dashboard con vehículos estacionados en este momento.",
        "reportes_comparativos":     "Comparación de recaudación, infracciones y ocupación entre períodos.",
        "balance_por_dominio":       "Estado de cuenta por domicilio o patente: historial de pagos e infracciones.",
        "areas_reservadas":          "Gestión de espacios reservados (discapacidad, carga/descarga, etc.).",
        "geolocalizacion_inspector": "Seguimiento en tiempo real de los inspectores en el mapa.",
        "notificaciones_conductor":  "Alertas por SMS o push cuando se labre un acta o venza el tiempo.",
        "informes_automaticos":      "Envío programado de reportes por correo a tesorero o autoridades.",
        "descuentos_voluntarios":    "Descuento automático si el infractor paga antes de que el inspector regrese.",
        "comisiones_vendedores":     "Liquidación de comisiones para vendedores de estacionamiento.",
        "reintegro_residentes":      "Reintegro de tiempo estacionado para vecinos del municipio.",
        "cobrador_inspector":        "Inspectores pueden cobrar infracciones directamente en campo.",
    }

    # Lista unificada: todos los módulos del sistema, activos o no
    todos_modulos = []
    for clave, nombre in ModuloMunicipio.MODULOS:
        instancia = modulos_activos.get(clave)
        todos_modulos.append({
            "clave":       clave,
            "nombre":      nombre,
            "descripcion": descripciones_modulos.get(clave, ""),
            "instancia":   instancia,   # None si nunca se creó
            "activo":      instancia.activo if instancia else False,
            "precio":      instancia.precio_mensual if instancia else Decimal("0"),
            "porcentaje":  instancia.porcentaje_modulo if instancia else Decimal("0"),
        })

    return render(request, "superadmin/editar_municipio.html", {
        "municipio":      municipio,
        "admins":         admins,
        "tesoreros":      tesoreros,
        "todos_modulos":  todos_modulos,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Gestión de admins
# ─────────────────────────────────────────────────────────────────────────────

@require_role("superadmin")
def crear_admin(request, municipio_id):
    """
    Crea un usuario de staff (admin o tesorero) para el municipio indicado.
    El superadmin elige el rol, correo, nombre y contraseña inicial.
    """
    municipio = get_object_or_404(Municipio, id=municipio_id)

    if request.method == "POST":
        correo     = request.POST.get("correo", "").strip().lower()
        first_name = request.POST.get("first_name", "").strip().title()
        last_name  = request.POST.get("last_name", "").strip().title()
        password   = request.POST.get("password", "").strip()
        rol        = request.POST.get("rol", "admin")  # "admin" o "tesorero"

        if not correo or not password:
            messages.error(request, "Correo y contraseña son obligatorios.")
            return redirect("crear_admin", municipio_id=municipio_id)

        if error_pwd := _error_password(password):
            messages.error(request, error_pwd)
            return redirect("crear_admin", municipio_id=municipio_id)

        if Usuario.objects.filter(correo=correo).exists():
            messages.error(request, f"Ya existe un usuario con el correo '{correo}'.")
            return redirect("crear_admin", municipio_id=municipio_id)

        with transaction.atomic():
            Usuario.objects.create(
                correo=correo,
                first_name=first_name,
                last_name=last_name,
                password=make_password(password),
                municipio=municipio,
                es_admin=(rol == "admin"),
                es_tesorero=(rol == "tesorero"),
                es_conductor=False,
                is_active=True,
            )

        label = "Admin" if rol == "admin" else "Tesorero"
        messages.success(request, f"{label} '{correo}' creado para {municipio.nombre}.")
        return redirect("editar_municipio", municipio_id=municipio_id)

    return render(request, "superadmin/crear_admin.html", {
        "municipio": municipio,
    })


@require_role("superadmin")
def toggle_admin(request, admin_id):
    """
    Activa o desactiva un usuario admin (sin eliminarlo).
    Solo acepta POST.
    """
    admin = get_object_or_404(Usuario, id=admin_id, es_admin=True)

    if request.method != "POST":
        return redirect("panel_superadmin")

    admin.is_active = not admin.is_active
    admin.save(update_fields=["is_active"])
    estado = "activado" if admin.is_active else "desactivado"
    messages.success(request, f"Admin {admin.correo} {estado}.")
    return redirect("editar_municipio", municipio_id=admin.municipio_id)


# ─────────────────────────────────────────────────────────────────────────────
# Gestión de módulos de pago
# ─────────────────────────────────────────────────────────────────────────────

@require_role("superadmin")
def gestionar_modulo(request, municipio_id):
    """
    Activa, desactiva o actualiza precios de módulos para un municipio.
    Acepta solo POST desde el panel de edición del municipio.

    Acciones POST:
        activar   → crea ModuloMunicipio si no existe, o lo reactiva; guarda precios
        desactivar → pone activo=False (no elimina el registro)
    """
    municipio = get_object_or_404(Municipio, id=municipio_id)

    if request.method != "POST":
        return redirect("editar_municipio", municipio_id=municipio_id)

    accion = request.POST.get("accion", "")
    modulo = request.POST.get("modulo", "").strip()

    # Validar que el módulo sea uno de los conocidos
    modulos_validos = {clave for clave, _ in ModuloMunicipio.MODULOS}
    if modulo not in modulos_validos:
        messages.error(request, "Módulo desconocido.")
        return redirect("editar_municipio", municipio_id=municipio_id)

    def _dec(key):
        try:
            return Decimal(request.POST.get(key, "0") or "0")
        except Exception:
            return Decimal("0")

    if accion == "activar":
        precio     = _dec("precio_mensual")
        porcentaje = _dec("porcentaje_modulo")
        obj, creado = ModuloMunicipio.objects.get_or_create(
            municipio=municipio,
            modulo=modulo,
            defaults={
                "activo":            True,
                "precio_mensual":    precio,
                "porcentaje_modulo": porcentaje,
                "activado_por":      request.user,
            }
        )
        if not creado:
            obj.activo            = True
            obj.precio_mensual    = precio
            obj.porcentaje_modulo = porcentaje
            obj.save(update_fields=["activo", "precio_mensual", "porcentaje_modulo"])

        nombre = dict(ModuloMunicipio.MODULOS).get(modulo, modulo)
        messages.success(request, f"Módulo '{nombre}' activado para {municipio.nombre}.")

    elif accion == "desactivar":
        ModuloMunicipio.objects.filter(municipio=municipio, modulo=modulo).update(activo=False)
        nombre = dict(ModuloMunicipio.MODULOS).get(modulo, modulo)
        messages.success(request, f"Módulo '{nombre}' desactivado.")

    return redirect("editar_municipio", municipio_id=municipio_id)


# ─────────────────────────────────────────────────────────────────────────────
# Importación de estacionamientos desde Excel (sistema anterior)
# ─────────────────────────────────────────────────────────────────────────────

def _parsear_cuadra(texto_cuadra):
    """
    Convierte el formato del Excel "16 750" en (calle, altura).

    El Excel usa "CALLE ALTURA" donde CALLE puede tener espacios
    (ej: "Av San Martín 350"). Tomamos todo excepto el último token
    como calle, y el último token como altura entera.

    Devuelve (calle: str, altura: int) o lanza ValueError si no se puede parsear.
    """
    partes = str(texto_cuadra).strip().split()
    if len(partes) < 2:
        raise ValueError(f"Formato de cuadra inválido: '{texto_cuadra}'")
    try:
        altura = int(partes[-1])
    except ValueError:
        raise ValueError(f"Altura no es un número en cuadra: '{texto_cuadra}'")
    calle = " ".join(partes[:-1])
    return calle, altura


@require_role("superadmin")
def importar_estacionamientos(request, municipio_id):
    """
    Importa estacionamientos activos desde el Excel del sistema anterior.

    Formato esperado (TransactionInfo.xlsx):
    - Fila 1: título (se ignora)
    - Fila 2: encabezados (se ignora)
    - Filas 3+: datos con columnas:
        Domino, Hora de Transacción, Desde, Desde Ingresado, Hasta,
        Cuadra, Zona, Interfaz, Inspector, Teléfono, Monto, Tarjeta, -, Local

    Lógica de importación:
    - hora_inicio = now() (el estacionamiento arranca desde este momento)
    - duracion_horas = Hasta - Desde del Excel (se preserva la duración original)
    - usuario = null si no hay teléfono (no se toca saldo)
    - subcuadra: se crea si no existe en el municipio
    - vehículo: se crea si no existe
    - filas con error: se saltean y se incluyen en el reporte
    """
    import openpyxl

    municipio = get_object_or_404(Municipio, id=municipio_id)

    if request.method != "POST":
        return render(request, "superadmin/importar_excel.html", {
            "municipio": municipio,
        })

    archivo = request.FILES.get("archivo")
    if not archivo:
        messages.error(request, "Seleccioná un archivo Excel.")
        return redirect("importar_estacionamientos", municipio_id=municipio_id)

    # Validar extensión
    if not archivo.name.lower().endswith((".xlsx", ".xls")):
        messages.error(request, "El archivo debe ser .xlsx o .xls.")
        return redirect("importar_estacionamientos", municipio_id=municipio_id)

    # Validar tamaño antes de abrir con openpyxl.
    # Sin este chequeo, un archivo muy grande puede agotar la memoria del servidor
    # antes de que openpyxl devuelva un error.
    LIMITE_MB = 10
    if archivo.size > LIMITE_MB * 1024 * 1024:
        messages.error(request, f"El archivo no puede superar {LIMITE_MB} MB.")
        return redirect("importar_estacionamientos", municipio_id=municipio_id)

    try:
        wb = openpyxl.load_workbook(archivo, data_only=True)
        ws = wb.active
    except Exception as e:
        messages.error(request, f"No se pudo abrir el archivo: {e}")
        return redirect("importar_estacionamientos", municipio_id=municipio_id)

    errores      = []
    importados   = 0
    omitidos     = 0
    hora_inicio  = timezone.now()  # todos arrancan desde el mismo momento

    for num_fila, fila in enumerate(ws.iter_rows(min_row=3, values_only=True), start=3):

        # Fila completamente vacía → saltar
        if not any(fila):
            continue

        # Desempaquetar columnas (14 columnas en el formato del sistema anterior)
        try:
            (domino, hora_tx, desde, desde_ing, hasta,
             cuadra, zona, interfaz, inspector, telefono,
             monto, tarjeta, _col13, local) = fila
        except ValueError:
            errores.append({
                "fila": num_fila,
                "patente": "—",
                "error": f"Fila con {len(fila)} columnas (se esperan 14) — verificar formato",
            })
            omitidos += 1
            continue

        # Cada fila en su propia transacción para que un error no cancele todo
        try:
            with transaction.atomic():

                # ── 1. Patente ───────────────────────────────────────────────
                patente = sanitizar_patente(str(domino or ""))
                if not patente:
                    raise ValueError("Patente vacía o inválida")

                # ── 2. Duración ──────────────────────────────────────────────
                if not desde or not hasta:
                    raise ValueError("Faltan columnas Desde o Hasta")
                if not hasattr(desde, "hour") or not hasattr(hasta, "hour"):
                    raise ValueError("Desde/Hasta no son fechas válidas")

                duracion_segundos = (hasta - desde).total_seconds()
                if duracion_segundos <= 0:
                    raise ValueError(
                        f"Duración inválida: Desde={desde} Hasta={hasta}"
                    )
                # Redondear a 1 decimal (ej: 3600s → 1.0h, 5400s → 1.5h)
                duracion_horas = Decimal(str(round(duracion_segundos / 3600, 1)))

                # ── 3. Vehículo ──────────────────────────────────────────────
                vehiculo, _ = Vehiculo.objects.get_or_create(
                    patente=patente,
                    defaults={"municipio": municipio},
                )

                # ── 4. Conductor (opcional) ──────────────────────────────────
                # No tocamos saldo — solo vinculamos si existe en el sistema.
                usuario = None
                if telefono:
                    tel_str = str(int(telefono)) if isinstance(telefono, float) else str(telefono).strip()
                    usuario = Usuario.objects.filter(telefono=tel_str).first()

                # ── 5. Subcuadra ─────────────────────────────────────────────
                # Creamos si no existe; el admin puede renombrarlas después.
                nombre_cuadra = str(cuadra).strip() if cuadra else ""
                if not nombre_cuadra or nombre_cuadra == " ":
                    raise ValueError("Cuadra vacía")

                calle_str, altura_int = _parsear_cuadra(nombre_cuadra)
                subcuadra, _ = Subcuadra.objects.get_or_create(
                    municipio=municipio,
                    calle=calle_str,
                    altura=altura_int,
                )

                # ── 6. Verificar no duplicar estacionamiento activo ──────────
                if Estacionamiento.objects.filter(
                    vehiculo=vehiculo, estado="ACTIVO"
                ).exists():
                    raise ValueError(
                        f"Patente {patente} ya tiene un estacionamiento ACTIVO en el sistema"
                    )

                # ── 7. Monto ─────────────────────────────────────────────────
                try:
                    costo = Decimal(str(monto or 0))
                except InvalidOperation:
                    costo = Decimal("0")

                # ── 8. Crear estacionamiento ─────────────────────────────────
                Estacionamiento.objects.create(
                    vehiculo=vehiculo,
                    subcuadra=subcuadra,
                    usuario=usuario,
                    estado="ACTIVO",
                    hora_inicio=hora_inicio,
                    duracion_horas=duracion_horas,
                    costo_base=costo,
                    costo_final=costo,
                )
                importados += 1

        except Exception as e:
            errores.append({
                "fila":    num_fila,
                "patente": str(domino or "—"),
                "error":   str(e),
            })
            omitidos += 1

    return render(request, "superadmin/resultado_importacion.html", {
        "municipio":  municipio,
        "importados": importados,
        "omitidos":   omitidos,
        "errores":    errores,
        "total":      importados + omitidos,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Plantillas de documentos por municipio
# ─────────────────────────────────────────────────────────────────────────────

# Variables disponibles por tipo — se pasan al template para mostrar referencia
_VARIABLES_POR_TIPO = {
    "acta":             ["{patente}", "{numero_acta}", "{fecha}", "{hora}", "{subcuadra}", "{monto}", "{inspector}", "{motivo}"],
    "cobro_hora":       ["{patente}", "{fecha}", "{hora_inicio}", "{hora_fin}", "{duracion}", "{monto}"],
    "abono":            ["{patente}", "{mes}", "{anio}", "{monto}", "{vendedor}"],
    "cobro_infraccion": ["{patente}", "{numero_acta}", "{monto}", "{fecha_pago}"],
    "anulacion":        ["{patente}", "{numero_acta}", "{motivo_anulacion}"],
}


@require_role("superadmin")
def gestionar_plantillas(request, municipio_id):
    """
    El superadmin configura el texto de encabezado/cuerpo/pie de los comprobantes
    de un municipio.

    GET  → muestra el editor con los 5 tipos; cada tipo tiene sus 3 textareas.
    POST → guarda o actualiza la plantilla del tipo enviado.

    Si las 3 secciones llegan vacías → elimina la plantilla (vuelve al default).
    Si al menos una sección tiene texto → crea o actualiza.
    """
    municipio = get_object_or_404(Municipio, id=municipio_id)

    if request.method == "POST":
        tipo  = request.POST.get("tipo", "").strip()
        tipos_validos = [t[0] for t in PlantillaDocumento.TIPOS]

        if tipo not in tipos_validos:
            messages.error(request, "Tipo de plantilla inválido.")
            return redirect("gestionar_plantillas", municipio_id=municipio_id)

        encabezado = request.POST.get("encabezado", "").strip()
        cuerpo     = request.POST.get("cuerpo",     "").strip()
        pie        = request.POST.get("pie",         "").strip()

        if not encabezado and not cuerpo and not pie:
            # Sin contenido → eliminar plantilla (vuelve al default hardcodeado)
            eliminadas, _ = PlantillaDocumento.objects.filter(
                municipio=municipio, tipo=tipo
            ).delete()
            if eliminadas:
                messages.success(request, f"Plantilla '{tipo}' eliminada. El sistema usará el texto por defecto.")
            else:
                messages.info(request, "No había plantilla guardada para ese tipo.")
        else:
            # Crear o actualizar
            plantilla, creada = PlantillaDocumento.objects.update_or_create(
                municipio=municipio,
                tipo=tipo,
                defaults={
                    "encabezado": encabezado,
                    "cuerpo":     cuerpo,
                    "pie":        pie,
                },
            )
            accion = "guardada" if creada else "actualizada"
            messages.success(request, f"Plantilla '{plantilla.get_tipo_display()}' {accion}.")

        return redirect("gestionar_plantillas", municipio_id=municipio_id)

    # GET: armar contexto con las plantillas existentes indexadas por tipo
    plantillas_existentes = {
        p.tipo: p
        for p in PlantillaDocumento.objects.filter(municipio=municipio)
    }

    # Construir lista de tipos con su plantilla (o None) y sus variables disponibles
    tipos_con_plantilla = [
        {
            "tipo":      tipo,
            "label":     label,
            "plantilla": plantillas_existentes.get(tipo),
            "variables": _VARIABLES_POR_TIPO.get(tipo, []),
        }
        for tipo, label in PlantillaDocumento.TIPOS
    ]

    return render(request, "superadmin/plantillas.html", {
        "municipio":          municipio,
        "tipos_con_plantilla": tipos_con_plantilla,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Liquidaciones de plataforma (cobro de Leandro a los municipios)
# ─────────────────────────────────────────────────────────────────────────────

def _calcular_recaudacion(municipio, desde, hasta):
    """
    Calcula la recaudación del municipio en el período según su `concepto_recaudacion`.

    - 'cierre_caja': suma CierreCaja.monto_municipio en el período (lo que el municipio
      retiene después de las comisiones de vendedores). Es el dato más completo.
    - 'rendiciones': suma Rendicion.total_neto validadas en el período.
    - 'manual': devuelve 0 para que el operador lo complete a mano.
    """
    from decimal import Decimal
    concepto = municipio.concepto_recaudacion

    if concepto == "cierre_caja":
        return CierreCaja.objects.filter(
            usuario__municipio=municipio,
            fecha_cierre__date__gte=desde,
            fecha_cierre__date__lte=hasta,
        ).aggregate(total=Sum("monto_municipio"))["total"] or Decimal("0")

    if concepto == "rendiciones":
        return Rendicion.objects.filter(
            municipio=municipio,
            estado="validada",
            creado_en__date__gte=desde,
            creado_en__date__lte=hasta,
        ).aggregate(total=Sum("total_neto"))["total"] or Decimal("0")

    return Decimal("0")   # 'manual'


@require_role("superadmin")
def liquidaciones_plataforma(request):
    """
    Lista todas las liquidaciones de plataforma de todos los municipios.
    Filtrable por estado y municipio.
    """
    estado_filtro   = request.GET.get("estado", "")
    municipio_filtro = request.GET.get("municipio_id", "")

    qs = LiquidacionPlataforma.objects.select_related("municipio").order_by("-periodo_fin", "-creado_en")
    if estado_filtro:
        qs = qs.filter(estado=estado_filtro)
    if municipio_filtro:
        qs = qs.filter(municipio_id=municipio_filtro)

    municipios = Municipio.objects.filter(activo=True).order_by("nombre")

    # Contadores para el header
    pendientes_pago       = LiquidacionPlataforma.objects.filter(estado="pendiente_pago").count()
    comprobantes_enviados = LiquidacionPlataforma.objects.filter(estado="comprobante_enviado").count()

    return render(request, "superadmin/liquidaciones_plataforma.html", {
        "liquidaciones":          qs[:100],
        "municipios":             municipios,
        "estado_filtro":          estado_filtro,
        "municipio_filtro":       municipio_filtro,
        "pendientes_pago":        pendientes_pago,
        "comprobantes_enviados":  comprobantes_enviados,
        "estados":                LiquidacionPlataforma.ESTADOS,
    })


@require_role("superadmin")
def crear_liquidacion_plataforma(request, municipio_id):
    """
    Superadmin crea una nueva liquidación para un municipio.

    GET: muestra formulario con montos calculados automáticamente según
         la configuración del municipio (cuota + porcentaje + período).
    POST: guarda la liquidación. Si sube factura, pasa a 'pendiente_pago'.
          Si no, queda en 'borrador'.
    """
    from datetime import date as _date
    from decimal import Decimal

    municipio = get_object_or_404(Municipio, id=municipio_id)

    if request.method == "POST":
        desde_str = request.POST.get("periodo_inicio", "")
        hasta_str = request.POST.get("periodo_fin", "")
        try:
            desde = _date.fromisoformat(desde_str)
            hasta = _date.fromisoformat(hasta_str)
        except ValueError:
            messages.error(request, "Fechas de período inválidas.")
            return redirect("crear_liquidacion_plataforma", municipio_id=municipio_id)

        # Montos: el superadmin puede editarlos manualmente en el formulario
        def _dec(nombre, default=Decimal("0")):
            val = request.POST.get(nombre, "").strip().replace(",", ".")
            try:
                return Decimal(val)
            except Exception:
                return default

        recaudacion_base = _dec("recaudacion_base")
        monto_fijo       = _dec("monto_fijo")
        monto_variable   = _dec("monto_variable")
        monto_total      = monto_fijo + monto_variable

        liq = LiquidacionPlataforma(
            municipio        = municipio,
            periodo_inicio   = desde,
            periodo_fin      = hasta,
            recaudacion_base = recaudacion_base,
            monto_fijo       = monto_fijo,
            monto_variable   = monto_variable,
            monto_total      = monto_total,
            iniciado_por     = "superadmin",
            notas_superadmin = request.POST.get("notas_superadmin", "").strip(),
            estado           = "borrador",
        )

        # Si subió la factura, pasa directo a "pendiente_pago"
        if "factura" in request.FILES:
            liq.factura = request.FILES["factura"]
            liq.estado  = "pendiente_pago"

        liq.save()
        messages.success(
            request,
            f"Liquidación creada para {municipio.nombre}. "
            + ("La factura fue adjuntada — el tesorero ya puede verla." if liq.estado == "pendiente_pago" else "Guardada como borrador."),
        )
        return redirect("detalle_liquidacion_plataforma", liquidacion_id=liq.id)

    # GET: calcular montos sugeridos
    hoy       = timezone.localtime().date()
    # Período sugerido: mes anterior completo
    if hoy.month == 1:
        desde_sugerido = _date(hoy.year - 1, 12, 1)
        hasta_sugerido = _date(hoy.year - 1, 12, 31)
    else:
        import calendar
        desde_sugerido = _date(hoy.year, hoy.month - 1, 1)
        _, ultimo_dia  = calendar.monthrange(hoy.year, hoy.month - 1)
        hasta_sugerido = _date(hoy.year, hoy.month - 1, ultimo_dia)

    recaudacion_calculada = _calcular_recaudacion(municipio, desde_sugerido, hasta_sugerido)

    # Sumar aportes de módulos activos al monto fijo y al porcentaje
    modulos_activos = ModuloMunicipio.objects.filter(municipio=municipio, activo=True)
    extra_fijo      = sum(m.precio_mensual    for m in modulos_activos)
    extra_pct       = sum(m.porcentaje_modulo for m in modulos_activos)

    monto_fijo_sugerido     = (municipio.cuota_mantenimiento_mensual or Decimal("0")) + extra_fijo
    porcentaje              = (municipio.porcentaje_plataforma or Decimal("0")) + extra_pct
    monto_variable_sugerido = (recaudacion_calculada * porcentaje / 100).quantize(Decimal("0.01"))

    return render(request, "superadmin/crear_liquidacion_plataforma.html", {
        "municipio":               municipio,
        "desde_sugerido":          desde_sugerido,
        "hasta_sugerido":          hasta_sugerido,
        "recaudacion_calculada":   recaudacion_calculada,
        "monto_fijo_sugerido":     monto_fijo_sugerido,
        "monto_variable_sugerido": monto_variable_sugerido,
        "monto_total_sugerido":    monto_fijo_sugerido + monto_variable_sugerido,
    })


@require_role("superadmin")
def detalle_liquidacion_plataforma(request, liquidacion_id):
    """
    Vista de detalle/acción de una liquidación.

    Acciones que puede hacer el superadmin:
    - Subir la factura (→ pendiente_pago)
    - Aprobar (→ aprobada)
    - Observar (→ observada)
    - Volver a pendiente_pago desde observada
    """
    liq = get_object_or_404(LiquidacionPlataforma, id=liquidacion_id)

    if request.method == "POST":
        accion = request.POST.get("accion", "")

        if accion == "subir_factura":
            if "factura" in request.FILES:
                if liq.factura:
                    liq.factura.delete(save=False)
                liq.factura = request.FILES["factura"]
                # Si estaba en borrador, avanzar
                if liq.estado == "borrador":
                    liq.estado = "pendiente_pago"
                liq.save(update_fields=["factura", "estado", "actualizado_en"])
                messages.success(request, "Factura subida. El tesorero ya puede verla.")
            else:
                messages.error(request, "No se adjuntó ningún archivo.")

        elif accion == "aprobar":
            if liq.estado not in ("comprobante_enviado", "observada", "pendiente_pago"):
                messages.warning(request, "Esta liquidación no está en estado para aprobar.")
            else:
                notas = request.POST.get("notas_superadmin", "").strip()
                liq.estado          = "aprobada"
                liq.aprobada_en     = timezone.now()
                liq.notas_superadmin = notas
                liq.save(update_fields=["estado", "aprobada_en", "notas_superadmin", "actualizado_en"])
                messages.success(request, f"Liquidación #{liq.id} aprobada. Pago confirmado.")

        elif accion == "observar":
            notas = request.POST.get("notas_superadmin", "").strip()
            liq.estado           = "observada"
            liq.notas_superadmin = notas
            liq.save(update_fields=["estado", "notas_superadmin", "actualizado_en"])
            messages.warning(request, f"Liquidación #{liq.id} marcada como observada.")

        elif accion == "reactivar":
            # Vuelve a pendiente_pago desde observada (para que el tesorero suba comprobante)
            if liq.estado == "observada":
                liq.estado = "pendiente_pago"
                liq.save(update_fields=["estado", "actualizado_en"])
                messages.info(request, "Liquidación reactivada a pendiente de pago.")

        elif accion == "solicitar_comprobante":
            # El superadmin le pide al tesorero que suba el comprobante de pago.
            # Registra la solicitud en notas para que el tesorero lo vea al abrir el detalle.
            if liq.estado == "aprobada":
                messages.warning(request, "La liquidación ya fue aprobada.")
            elif liq.comprobante_pago:
                messages.info(request, "El tesorero ya subió un comprobante.")
            else:
                from django.utils import timezone as _tz
                timestamp = _tz.localtime().strftime("%d/%m/%Y %H:%M")
                nota_solicitud = f"⚠️ El superadmin solicita el comprobante de pago ({timestamp})."
                notas_previas = liq.notas_superadmin or ""
                liq.notas_superadmin = f"{nota_solicitud}\n{notas_previas}".strip()
                liq.save(update_fields=["notas_superadmin", "actualizado_en"])
                messages.success(request, "Solicitud de comprobante registrada. El tesorero la verá en el detalle.")

        return redirect("detalle_liquidacion_plataforma", liquidacion_id=liq.id)

    return render(request, "superadmin/detalle_liquidacion_plataforma.html", {
        "liq": liq,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Sugerencias de mejora — panel superadmin
# ─────────────────────────────────────────────────────────────────────────────

@require_role("superadmin")
def panel_sugerencias(request):
    """
    Lista todas las sugerencias de todos los municipios.
    Filtros: estado, criticidad, area, municipio.
    """
    qs = SugerenciaMejora.objects.select_related("usuario", "municipio").order_by("-creado_en")

    estado_filtro     = request.GET.get("estado", "").strip()
    criticidad_filtro = request.GET.get("criticidad", "").strip()
    area_filtro       = request.GET.get("area", "").strip()

    if estado_filtro:
        qs = qs.filter(estado=estado_filtro)
    if criticidad_filtro:
        qs = qs.filter(criticidad=criticidad_filtro)
    if area_filtro:
        qs = qs.filter(area=area_filtro)

    # Contadores para badges en el panel
    pendientes_count = SugerenciaMejora.objects.filter(
        estado__in=("recibida", "en_revision")
    ).count()

    return render(request, "superadmin/sugerencias.html", {
        "sugerencias":        qs,
        "pendientes_count":   pendientes_count,
        "estado_filtro":      estado_filtro,
        "criticidad_filtro":  criticidad_filtro,
        "area_filtro":        area_filtro,
        "estados":            SugerenciaMejora.ESTADOS,
        "criticidades":       SugerenciaMejora.CRITICIDAD,
        "areas":              SugerenciaMejora.AREAS,
    })


@require_role("superadmin")
def gestionar_sugerencia(request, sugerencia_id):
    """
    El superadmin cambia el estado de una sugerencia y puede dejar una respuesta.
    Al cambiar el estado se crea una Notificacion in-app para el usuario.
    """
    sugerencia = get_object_or_404(SugerenciaMejora, id=sugerencia_id)

    if request.method == "POST":
        nuevo_estado = request.POST.get("estado", sugerencia.estado)
        respuesta    = request.POST.get("respuesta", "").strip()

        estado_cambio = nuevo_estado != sugerencia.estado

        sugerencia.estado    = nuevo_estado
        sugerencia.respuesta = respuesta
        # Marcar como no-notificado para que el usuario lo vea al entrar
        if estado_cambio and sugerencia.usuario:
            sugerencia.notificado = False
        sugerencia.save(update_fields=["estado", "respuesta", "notificado", "actualizado_en"])

        # Crear notificación in-app si el estado cambió y hay usuario registrado
        if estado_cambio and sugerencia.usuario:
            etiquetas = {
                "en_revision":  "en revisión",
                "implementada": "implementada ✅",
                "descartada":   "descartada",
            }
            label = etiquetas.get(nuevo_estado, nuevo_estado)
            Notificacion.objects.create(
                destinatario = sugerencia.usuario,
                mensaje      = (
                    f"Tu sugerencia «{sugerencia.titulo}» pasó a estado: {label}."
                    + (f" Respuesta: {respuesta}" if respuesta else "")
                ),
            )

        messages.success(request, "Sugerencia actualizada.")
        return redirect("panel_sugerencias")

    return render(request, "superadmin/detalle_sugerencia.html", {
        "sugerencia": sugerencia,
        "estados":    SugerenciaMejora.ESTADOS,
    })
