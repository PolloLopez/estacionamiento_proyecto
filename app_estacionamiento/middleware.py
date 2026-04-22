# sitio/middleware.py

class UsuarioMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        print("🧪 SESSION:", request.session.items())

        # 🔥 Compatibilidad temporal
        request.usuario = request.user if request.user.is_authenticated else None

        print("🧪 request.user:", request.user)
        print("🧪 request.usuario:", request.usuario)

        return self.get_response(request)