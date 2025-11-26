from functools import wraps
from django.shortcuts import redirect

def require_login(view_func):
    """
    Decorador que exige que el usuario esté logueado.
    Si no hay sesión, redirige al login.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get("usuario_id"):
            return redirect("login")
        return view_func(request, *args, **kwargs)
    return wrapper
