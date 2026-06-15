# app_estacionamiento/middleware.py

from django.shortcuts import redirect
from django.urls import reverse


# URLs que se pueden acceder sin tener municipio asignado.
# Se usa startswith() para cubrir variantes con parámetros.
URLS_EXENTAS_DE_MUNICIPIO = [
    "/usuarios/completar-perfil/",
    "/usuarios/logout/",
    "/accounts/",         # allauth (Google OAuth)
    "/admin/",            # Django admin
]


class RequiereMunicipioMiddleware:
    """
    Si el usuario está logueado pero no tiene municipio asignado,
    y el sistema tiene más de un municipio activo, lo redirige
    a /usuarios/completar-perfil/ para que elija uno.

    En sistemas de un solo municipio el adapter ya lo asigna automáticamente
    al hacer login con Google, por lo que este middleware nunca actúa.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self._debe_redirigir(request):
            return redirect("completar_perfil")
        return self.get_response(request)

    def _debe_redirigir(self, request):
        # Solo actúa sobre usuarios autenticados sin municipio
        if not request.user.is_authenticated:
            return False

        if request.user.municipio_id:
            return False

        # Evitar loop: no redirigir si ya está en una URL exenta
        ruta = request.path
        for url_exenta in URLS_EXENTAS_DE_MUNICIPIO:
            if ruta.startswith(url_exenta):
                return False

        # Solo redirigir si hay más de un municipio.
        # Importación tardía para evitar problemas de arranque de Django.
        from .models import Municipio
        return Municipio.objects.filter(activo=True).count() > 1
