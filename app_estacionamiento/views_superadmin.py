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
"""

from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .decorators import require_role
from .models import ModuloMunicipio, Municipio, Usuario


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

        # Edición general
        municipio.nombre              = request.POST.get("nombre", municipio.nombre).strip()
        municipio.comision_vendedor   = request.POST.get("comision_vendedor", municipio.comision_vendedor)
        municipio.activo              = request.POST.get("activo") == "on"
        municipio.save()
        messages.success(request, "Municipio actualizado.")
        return redirect("panel_superadmin")

    admins = Usuario.objects.filter(municipio=municipio, es_admin=True).order_by("-is_active", "correo")
    modulos = ModuloMunicipio.objects.filter(municipio=municipio)

    # Módulos disponibles que aún no están asignados
    modulos_asignados = set(modulos.values_list("modulo", flat=True))
    modulos_disponibles = [
        (clave, nombre)
        for clave, nombre in ModuloMunicipio.MODULOS
        if clave not in modulos_asignados
    ]

    return render(request, "superadmin/editar_municipio.html", {
        "municipio":          municipio,
        "admins":             admins,
        "modulos":            modulos,
        "modulos_disponibles": modulos_disponibles,
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
