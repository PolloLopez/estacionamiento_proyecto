# app_estacionamiento/decorators.py
from functools import wraps
from django.shortcuts import redirect, get_object_or_404
from app_estacionamiento.models import Usuario

def require_login(view_func):

    """
    Decorador que exige que haya sesión iniciada.
    - Si no hay usuario en sesión, redirige al login (302).
    - Si hay sesión, ejecuta la vista normalmente.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        usuario_id = request.session.get("usuario_id")
        if not usuario_id:
            # 302 → redirige al login
            return redirect("login")
        return view_func(request, *args, **kwargs)
    return _wrapped_view



def require_role(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("login")

            usuario = request.user
            if (
                ("conductor" in roles and usuario.es_conductor)
                or ("inspector" in roles and usuario.es_inspector)
                or ("vendedor" in roles and usuario.es_vendedor)
                or ("admin" in roles and usuario.es_admin)
            ):
                return view_func(request, *args, **kwargs)

            return redirect("inicio")
        return _wrapped_view
    return decorator

    """
    Decorador que exige que el usuario tenga al menos uno de los roles dados.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            
            usuario_id = request.session.get("usuario_id")
            if not usuario_id:
                return redirect("login")   # ✅ redirige si no hay sesión

            try:
                usuario = Usuario.objects.get(id=usuario_id)
            except Usuario.DoesNotExist:
                return redirect("login")

            # Verificar roles
            if (
                ("conductor" in roles and usuario.es_conductor)
                or ("inspector" in roles and usuario.es_inspector)
                or ("vendedor" in roles and usuario.es_vendedor)
                or ("admin" in roles and usuario.es_admin)
            ):
                return view_func(request, *args, **kwargs)

            # ✅ redirige si no cumple rol
            return redirect("inicio")
        return _wrapped_view
    return decorator