from functools import wraps
from django.shortcuts import redirect, get_object_or_404
from .models import Usuario

def require_role(*roles):
    """
    Decorador que valida que el usuario esté logueado y tenga alguno de los roles permitidos.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # 1. Chequeo de sesión
            usuario_id = request.session.get("usuario_id")
            if not usuario_id:
                return redirect("login")

            usuario = get_object_or_404(Usuario, id=usuario_id)

            # 2. Chequeo de rol
            rol_ok = False
            for rol in roles:
                if getattr(usuario, f"es_{rol}", False):
                    rol_ok = True
                    break

            # 3. Redirección segura si falla
            if not rol_ok:
                return redirect("inicio")

            # Si todo bien, ejecuta la vista
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def require_login(view_func):
    """
    Decorador que exige que el usuario esté logueado.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        usuario_id = request.session.get("usuario_id")
        if not "usuario_id":
            return redirect("login")
        return view_func(request, *args, **kwargs)
    return _wrapped_view
