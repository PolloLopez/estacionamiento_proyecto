# app_estacionamiento/decorators.py
from functools import wraps
from django.shortcuts import redirect, get_object_or_404
from app_estacionamiento.models import Usuario

def require_login(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        usuario_id = request.session.get("usuario_id")
        if not usuario_id:
            return redirect("login")
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def require_role(*roles):
    """
    Decorador que exige que el usuario tenga al menos uno de los roles dados.
    Además asigna el objeto Usuario al request.user para usarlo en templates.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            usuario_id = request.session.get("usuario_id")
            if not usuario_id:
                return redirect("login")

            try:
                usuario = Usuario.objects.get(id=usuario_id)
            except Usuario.DoesNotExist:
                return redirect("login")

            # Asignar el usuario al request para que esté disponible en templates
            request.user = usuario

            # Verificar roles
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