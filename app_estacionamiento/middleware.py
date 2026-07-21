# app_estacionamiento/middleware.py

from django.shortcuts import redirect
from django.urls import reverse


# URLs que se pueden acceder sin tener municipio asignado.
# Se usa startswith() para cubrir variantes con parámetros.
URLS_EXENTAS_DE_MUNICIPIO = [
    "/completar-perfil/",
    "/logout/",
    "/accounts/",         # allauth (Google OAuth)
    "/sistema-interno/",  # Django admin
]


class RequiereMunicipioMiddleware:
    """
    Si el usuario está logueado pero no tiene municipio asignado,
    y el sistema tiene más de un municipio activo, lo redirige
    a /completar-perfil/ para que elija uno.

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
        # Solo actúa sobre usuarios autenticados
        if not request.user.is_authenticated:
            return False

        # Evitar loop: no redirigir si ya está en una URL exenta
        ruta = request.path
        for url_exenta in URLS_EXENTAS_DE_MUNICIPIO:
            if ruta.startswith(url_exenta):
                return False

        # Sin municipio y hay más de uno activo → elegir municipio
        if not request.user.municipio_id:
            from .models import Municipio
            return Municipio.objects.filter(activo=True).count() > 1

        # Conductor sin nombre (puede ocurrir con cuentas Google sin given_name)
        if request.user.es_conductor and not request.user.first_name:
            return True

        return False
