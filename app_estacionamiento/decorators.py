from functools import wraps
from django.shortcuts import redirect, get_object_or_404
from .models import Usuario

def require_role(*roles):
    """
    Decorador para restringir acceso a vistas según rol.
    Ejemplo: @require_role("conductor", "admin")
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            usuario_id = request.session.get("usuario_id")
            if not usuario_id:
                return redirect("login")

            usuario = get_object_or_404(Usuario, id=usuario_id)

            role_map = {
                "admin": usuario.es_admin,
                "inspector": usuario.es_inspector,
                "vendedor": usuario.es_vendedor,
                "conductor": usuario.es_conductor,
            }

            if any(role_map.get(r, False) for r in roles):
                return view_func(request, *args, **kwargs)

            return redirect("inicio")
        return wrapper
    return decorator

def require_login(view_func):
    """
    Decorador que exige que el usuario esté logueado.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get("usuario_id"):
            return redirect("login")
        return view_func(request, *args, **kwargs)
    return wrapper
