# utils.py

def get_usuario(request):
    return request.user if request.user.is_authenticated else None