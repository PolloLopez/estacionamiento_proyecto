# app_estacionamiento/decorators.py

from functools import wraps
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.db.models import Q


def require_login(view_func):
    """
    Verifica que exista un usuario autenticado.

    Si no hay sesión válida:
    → redirige al login.

    Si hay sesión:
    → continúa normalmente.
    """

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):

        # request.user existe SIEMPRE
        # pero puede ser AnonymousUser
        if not request.user.is_authenticated:
            return redirect("login")

        return view_func(request, *args, **kwargs)

    return _wrapped_view


def require_role(*roles):
    """
    Decorador de autorización por roles.

    Ejemplo:
        @require_role("admin")
        @require_role("inspector", "admin")

    Roles soportados:
        - admin
        - inspector
        - vendedor
        - conductor
    """

    def decorator(view_func):

        @wraps(view_func)
        def wrapper(request, *args, **kwargs):

            # ==========================================
            # 1. VALIDAR LOGIN
            # ==========================================
            if not request.user.is_authenticated:
                return redirect("login")

            usuario = request.user

            # ==========================================
            # 2. VALIDAR ROLES
            # ==========================================
            tiene_permiso = any([

                # ADMIN
                (
                    "admin" in roles and (
                        usuario.is_superuser
                        or usuario.is_staff
                        or getattr(usuario, "es_admin", False)
                    )
                ),

                # INSPECTOR
                (
                    "inspector" in roles and
                    getattr(usuario, "es_inspector", False)
                ),

                # VENDEDOR
                (
                    "vendedor" in roles and
                    getattr(usuario, "es_vendedor", False)
                ),

                # CONDUCTOR
                (
                    "conductor" in roles and
                    getattr(usuario, "es_conductor", False)
                ),

                # TESORERO
                (
                    "tesorero" in roles and
                    getattr(usuario, "es_tesorero", False)
                ),

                # SUPERADMIN (rol global — sin municipio propio)
                (
                    "superadmin" in roles and
                    getattr(usuario, "es_superadmin", False)
                ),
            ])

            # ==========================================
            # 3. BLOQUEAR SI NO TIENE PERMISOS
            # ==========================================
            if not tiene_permiso:
                # Render con template completo: navbar, estilos y botón de volver.
                return TemplateResponse(request, "403.html", status=403)

            # ==========================================
            # 4. CONTINUAR VIEW
            # ==========================================
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


def require_modulo(nombre_modulo):
    """
    Verifica que el municipio del usuario tenga activo el módulo de pago indicado.

    Uso:
        @require_modulo("geolocalizacion_inspector")

    Si el municipio no tiene el módulo activo, muestra la pantalla
    'módulo no disponible' en vez de un 403 genérico.

    Nota: el superadmin puede acceder a todo sin restricción de módulos,
    porque necesita poder configurar y probar cada módulo.
    """

    def decorator(view_func):

        @wraps(view_func)
        def wrapper(request, *args, **kwargs):

            if not request.user.is_authenticated:
                return redirect("login")

            usuario = request.user

            # El superadmin pasa siempre — puede gestionar y probar cualquier módulo
            if getattr(usuario, "es_superadmin", False):
                return view_func(request, *args, **kwargs)

            # Para el resto: verificar que el municipio tenga el módulo activo
            municipio = getattr(usuario, "municipio", None)
            if not municipio:
                return TemplateResponse(request, "403.html", status=403)

            # Import local para evitar importación circular con models
            from .models import ModuloMunicipio
            tiene_modulo = ModuloMunicipio.objects.filter(
                municipio=municipio,
                modulo=nombre_modulo,
                activo=True,
            ).exists()

            if not tiene_modulo:
                return TemplateResponse(request, "modulo_no_disponible.html", {
                    "modulo": nombre_modulo,
                }, status=402)

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator