# sitio/middleware.py

from app_estacionamiento.models import Usuario

class UsuarioMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        print("🧪 SESSION:", request.session.items())

        usuario_id = request.session.get("usuario_id")

        print("🧪 usuario_id:", usuario_id)

        request.usuario = None

        if usuario_id:
            request.usuario = Usuario.objects.filter(id=usuario_id).first()

        print("🧪 request.usuario:", request.usuario)

        return self.get_response(request)