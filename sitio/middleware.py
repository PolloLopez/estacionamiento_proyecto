#sitio/middleware.py
from app_estacionamiento.models import Usuario

class UsuarioMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        usuario_id = request.session.get("usuario_id")
        request.usuario = None

        if usuario_id:
            request.usuario = Usuario.objects.filter(id=usuario_id).first()

        return self.get_response(request)