# sitio/middleware.py

from app_estacionamiento.models import Usuario

class UsuarioMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        print("🧪 SESSION:", request.session.items())

        request.usuario = request.user if request.user.is_authenticated else None

        print("🧪 request.usuario:", request.usuario)

        return self.get_response(request)