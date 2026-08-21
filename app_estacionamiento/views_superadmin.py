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

from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .decorators import require_role
from .views_admin import _error_password
from .models import Estacionamiento, ModuloMunicipio, Municipio, PlantillaDocumento, Subcuadra, Usuario, Vehiculo
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

        # ── Campos de texto y número ──────────────────────────────────────
        # Para campos numéricos usamos helpers que ignoran string vacío:
        # request.POST.get(key, fallback) devuelve "" si el key existe pero está vacío,
        # no el fallback → asignar "" a un DecimalField/IntegerField explota en save().
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

        municipio.nombre             = request.POST.get("nombre", municipio.nombre).strip()
        municipio.nombre_sistema     = request.POST.get("nombre_sistema", "").strip()
        municipio.monto_minimo_carga        = _entero("monto_minimo_carga",        municipio.monto_minimo_carga)
        municipio.monto_maximo_carga        = _entero("monto_maximo_carga",        municipio.monto_maximo_carga)
        municipio.minutos_entre_infracciones = _entero("minutos_entre_infracciones", municipio.minutos_entre_infracciones)
        municipio.activo             = request.POST.get("activo") == "on"
        municipio.leyenda_horarios   = request.POST.get("leyenda_horarios", "").strip()
        municipio.texto_ordenanza    = request.POST.get("texto_ordenanza", "").strip()

        # ── Colores de branding ────────────────────────────────────────────
        # El input type=color sincroniza el valor con el text input vía JS.
        # Usamos el text input (que puede estar en blanco para "sin color").
        color_primario   = request.POST.get("color_primario_hex", "").strip()
        color_secundario = request.POST.get("color_secundario_hex", "").strip()
        if color_primario.startswith("#") and len(color_primario) in (4, 7):
            municipio.color_primario = color_primario
        if color_secundario.startswith("#") and len(color_secundario) in (4, 7):
            municipio.color_secundario = color_secundario

        # ── Logo ───────────────────────────────────────────────────────────
        if request.POST.get("borrar_logo") and municipio.logo:
            municipio.logo.delete(save=False)
            municipio.logo = None
        if "logo" in request.FILES:
            municipio.logo = request.FILES["logo"]

        # ── Ícono de app (PWA / acceso directo) ────────────────────────────
        if request.POST.get("borrar_icono_app") and municipio.icono_app:
            municipio.icono_app.delete(save=False)
            municipio.icono_app = None
        if "icono_app" in request.FILES:
            municipio.icono_app = request.FILES["icono_app"]

        municipio.save()
        messages.success(request, "Municipio actualizado.")
        return redirect("panel_superadmin")

    admins = Usuario.objects.filter(municipio=municipio, es_admin=True).order_by("-is_active", "correo")
    modulos = list(ModuloMunicipio.objects.filter(municipio=municipio))

    # Módulos disponibles que aún no están asignados
    modulos_asignados = set(m.modulo for m in modulos)
    modulos_disponibles = [
        (clave, nombre)
        for clave, nombre in ModuloMunicipio.MODULOS
        if clave not in modulos_asignados
    ]

    # Descripción de cada módulo para mostrar en el panel
    descripciones_modulos = {
        "ocupacion_tiempo_real":      "Mapa o dashboard con vehículos estacionados en este momento.",
        "reportes_comparativos":      "Comparación de recaudación, infracciones y ocupación entre períodos.",
        "balance_por_dominio":        "Estado de cuenta por domicilio o patente: historial de pagos e infracciones.",
        "areas_reservadas":           "Gestión de espacios reservados (discapacidad, carga/descarga, etc.).",
        "geolocalizacion_inspector":  "Seguimiento en tiempo real de los inspectores en el mapa.",
        "notificaciones_conductor":   "Alertas por SMS o push cuando se labre un acta o venza el tiempo.",
        "informes_automaticos":       "Envío programado de reportes por correo a tesorero o autoridades.",
    }

    # Anotar descripción en cada instancia para poder accederla desde el template
    for m in modulos:
        m.descripcion = descripciones_modulos.get(m.modulo, "")

    return render(request, "superadmin/editar_municipio.html", {
        "municipio":            municipio,
        "admins":               admins,
        "modulos":              modulos,
        "modulos_disponibles":  modulos_disponibles,
        "descripciones_modulos": descripciones_modulos,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Gestión de admins
# ─────────────────────────────────────────────────────────────────────────────

@require_role("superadmin")
def crear_admin(request, municipio_id):
    """
    Crea un nuevo usuario con rol admin para el municipio indicado.
    El superadmin define correo, nombre y contraseña inicial.
    """
    municipio = get_object_or_404(Municipio, id=municipio_id)

    if request.method == "POST":
        correo     = request.POST.get("correo", "").strip().lower()
        first_name = request.POST.get("first_name", "").strip().title()
        last_name  = request.POST.get("last_name", "").strip().title()
        password   = request.POST.get("password", "").strip()

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
                es_admin=True,
                es_conductor=False,
                is_active=True,
            )

        messages.success(request, f"Admin '{correo}' creado para {municipio.nombre}.")
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
    Activa, desactiva o actualiza el precio de un módulo para un municipio.
    Acepta solo POST desde el panel de edición del municipio.

    Acciones POST:
        activar   → crea ModuloMunicipio si no existe, o lo reactiva
        desactivar → pone activo=False (no elimina el registro)
        precio    → actualiza precio_mensual
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

    if accion == "activar":
        precio = request.POST.get("precio_mensual", "0") or "0"
        obj, creado = ModuloMunicipio.objects.get_or_create(
            municipio=municipio,
            modulo=modulo,
            defaults={
                "activo":         True,
                "precio_mensual": precio,
                "activado_por":   request.user,
            }
        )
        if not creado:
            obj.activo         = True
            obj.precio_mensual = precio
            obj.save(update_fields=["activo", "precio_mensual"])

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
