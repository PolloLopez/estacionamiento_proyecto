# app_estacionamiento/decorators.py
from functools import wraps
from django.shortcuts import redirect
from django.http import HttpResponseForbidden

def require_login(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        usuario = request.user
        if not usuario:
            return redirect("login")
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def require_role(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):

            # 🔐 autenticación
            if not request.user.is_authenticated:
                return redirect("login")

            usuario = request.user

            # 🎭 roles unificados
            tiene_permiso = any([
                ("admin" in roles and (usuario.is_superuser or usuario.is_staff or getattr(usuario, "es_admin", False))),
                ("inspector" in roles and getattr(usuario, "es_inspector", False)),
                ("vendedor" in roles and getattr(usuario, "es_vendedor", False)),
                ("conductor" in roles and getattr(usuario, "es_conductor", False)),
            ])

            # 🔒 bloqueo correcto (SIN LOOP)
            if not tiene_permiso:
                return HttpResponseForbidden("No autorizado")

            return view_func(request, *args, **kwargs)

        return wrapper
    return decorator