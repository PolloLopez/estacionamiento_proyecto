# app_estacionamiento/decorators.py

from functools import wraps
from django.shortcuts import redirect
from django.http import HttpResponseForbidden


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
            ])

            # ==========================================
            # 3. BLOQUEAR SI NO TIENE PERMISOS
            # ==========================================
            if not tiene_permiso:
                return HttpResponseForbidden("No autorizado")

            # ==========================================
            # 4. CONTINUAR VIEW
            # ==========================================
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator