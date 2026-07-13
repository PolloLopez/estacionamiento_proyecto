# app_estacionamiento/views_auth.py
"""
Vistas de autenticación y perfil de usuario.

Responsabilidades:
- Login / logout
- Registro de nuevo conductor
- Redirección por rol al ingresar
- Completar perfil (OAuth sin nombre o sin municipio)

No incluye lógica de negocio de ningún rol específico.
"""

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import RegistroUsuarioForm
from .models import Municipio


# ─────────────────────────────────────────────────────────────────────────────
# Utilidad de redirección
# ─────────────────────────────────────────────────────────────────────────────

def redirect_por_rol(usuario):
    """
    Redirige al panel correcto según el rol del usuario autenticado.
    Usado después del login, registro y completar_perfil.
    """
    if usuario.es_admin:
        return redirect("panel_admin")
    elif usuario.es_inspector:
        return redirect("panel_inspectores")
    elif usuario.es_vendedor:
        return redirect("panel_vendedor")
    elif usuario.es_conductor:
        return redirect("inicio_usuarios")
    return redirect("login")


# ─────────────────────────────────────────────────────────────────────────────
# Entrada al sistema
# ─────────────────────────────────────────────────────────────────────────────

def home(request):
    """
    Raíz del sitio: redirige al login si no está autenticado,
    o al panel del rol si ya lo está.
    """
    if not request.user.is_authenticated:
        return redirect("login")
    return redirect("inicio")


@login_required
def inicio(request):
    """
    Despacha al panel correcto según el rol.
    Actúa como punto de entrada post-login para allauth y links genéricos.
    """
    return redirect_por_rol(request.user)


# ─────────────────────────────────────────────────────────────────────────────
# Login / Logout
# ─────────────────────────────────────────────────────────────────────────────

def login_view(request):
    """
    Login con email y contraseña.
    Si las credenciales son válidas, redirige al panel del rol.
    """
    if request.method == "POST":
        correo   = request.POST.get("correo")
        password = request.POST.get("password")

        usuario = authenticate(request, username=correo, password=password)

        if usuario is not None:
            login(request, usuario)
            return redirect_por_rol(usuario)

        return render(request, "usuarios/login.html", {
            "form": {"errors": True}
        })

    return render(request, "usuarios/login.html")


def logout_view(request):
    """
    Cierra la sesión. Solo acepta POST para prevenir logout por CSRF
    (links maliciosos como <img src='/logout/'>).
    """
    if request.method == "POST":
        logout(request)
    return redirect("login")


# ─────────────────────────────────────────────────────────────────────────────
# Registro
# ─────────────────────────────────────────────────────────────────────────────

def registro_view(request):
    """
    Registro de nuevo conductor con email y contraseña.
    Si el sistema tiene más de un municipio, el usuario elige el suyo en el form.
    Al registrarse queda logueado y se redirige a su panel.
    """
    if request.method == "POST":
        form = RegistroUsuarioForm(request.POST)

        if form.is_valid():
            usuario = form.save(commit=False)

            # Municipio: tomar del POST si hay más de uno disponible, sino el primero
            municipio_id = request.POST.get("municipio_id")
            if municipio_id:
                usuario.municipio = Municipio.objects.filter(id=municipio_id).first()
            else:
                usuario.municipio = Municipio.objects.first()

            usuario.save()
            login(request, usuario)
            return redirect_por_rol(usuario)

    else:
        form = RegistroUsuarioForm()

    return render(request, "usuarios/registro.html", {
        "form":       form,
        "municipios": Municipio.objects.filter(activo=True),
    })


# ─────────────────────────────────────────────────────────────────────────────
# Completar perfil (OAuth)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def completar_perfil(request):
    """
    Formulario de bienvenida para usuarios que entran por Google OAuth.

    Cubre dos casos que pueden ocurrir al mismo tiempo o por separado:
    1. Sin municipio asignado (sistema multi-municipio).
    2. Sin nombre/apellido (cuenta Google sin given_name/family_name).

    Una vez completado, redirige al panel según el rol.
    """
    usuario    = request.user
    municipios = Municipio.objects.filter(activo=True)

    falta_municipio = not usuario.municipio_id
    falta_nombre    = usuario.es_conductor and not usuario.first_name

    if request.method == "POST":
        errores = False

        municipio_obj = None
        if falta_municipio:
            municipio_id  = request.POST.get("municipio_id")
            municipio_obj = Municipio.objects.filter(id=municipio_id, activo=True).first()
            if not municipio_obj:
                messages.error(request, "Seleccioná un municipio válido.")
                errores = True

        nombre   = request.POST.get("nombre", "").strip()
        apellido = request.POST.get("apellido", "").strip()
        if falta_nombre and not nombre:
            messages.error(request, "El nombre es obligatorio.")
            errores = True

        if errores:
            return render(request, "usuarios/completar_perfil.html", {
                "municipios":      municipios,
                "falta_municipio": falta_municipio,
                "falta_nombre":    falta_nombre,
            })

        campos = []
        if falta_municipio and municipio_obj:
            usuario.municipio = municipio_obj
            campos.append("municipio")
        if falta_nombre and nombre:
            usuario.first_name = nombre
            campos.append("first_name")
            if apellido:
                usuario.last_name = apellido
                campos.append("last_name")

        if campos:
            usuario.save(update_fields=campos)

        messages.success(request, "¡Perfil completado! Ya podés usar el sistema.")
        return redirect_por_rol(usuario)

    return render(request, "usuarios/completar_perfil.html", {
        "municipios":      municipios,
        "falta_municipio": falta_municipio,
        "falta_nombre":    falta_nombre,
    })
