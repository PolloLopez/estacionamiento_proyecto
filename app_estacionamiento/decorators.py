# app_estacionamiento/decorators.py
from functools import wraps
from django.shortcuts import redirect
from app_estacionamiento.utils import get_usuario

def require_login(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        usuario = get_usuario(request)
        if not usuario:
            return redirect("login")
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def require_role(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            usuario = get_usuario(request)

            if not usuario:
                return redirect("login")

            if not any([
                ("admin" in roles and usuario.es_admin),
                ("inspector" in roles and usuario.es_inspector),
                ("vendedor" in roles and usuario.es_vendedor),
                ("conductor" in roles and usuario.es_conductor),
            ]):
                return redirect("inicio")

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator