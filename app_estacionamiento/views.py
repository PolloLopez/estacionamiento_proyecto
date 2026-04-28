# ESTACIONAMIENTO_APP/app_estacionamiento/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.contrib.auth import authenticate, login, logout
from django.urls import reverse
from decimal import Decimal
from .decorators import require_role, require_login
from .forms import RegistroUsuarioForm
from django.conf import settings
from django.contrib.auth.decorators import login_required
from app_estacionamiento.models import Usuario, Vehiculo, Subcuadra, Estacionamiento, Infraccion, VehiculoUsuario, Municipio
from app_estacionamiento.factories import EstacionamientoFactory

def get_subcuadra_default(municipio):
    return Subcuadra.objects.get_or_create(
        calle="Zona Única",
        altura=0,
        municipio=municipio
    )[0]

@login_required
def inicio(request):
    user = request.user

    if user.is_superuser or user.is_staff or getattr(user, "es_admin", False):
        return redirect("panel_admin")

    if getattr(user, "es_inspector", False):
        return redirect("panel_inspectores")

    if getattr(user, "es_vendedor", False):
        return redirect("panel_vendedores")

    return redirect("inicio_usuarios")

def login_view(request):
    if request.method == "POST":
        correo = request.POST.get("username")
        password = request.POST.get("password")

        usuario = authenticate(request, username=correo, password=password)

        if usuario is not None:

            login(request, usuario)

            return redirect("inicio")
        else:

            return render(request, "usuarios/login.html", {
                "form": {"errors": True}
            })

    return render(request, "usuarios/login.html")

@require_role("inspector", "admin", "conductor", "vendedor") 
def inicio_usuarios(request):
    usuario = request.user
         
    estacionamiento_activo = Estacionamiento.objects.filter(
    activo=True,
    registrado_por=usuario
    ).order_by("-hora_inicio").first()

    return render(request, "usuarios/inicio_usuarios.html", {
        "usuario": usuario,
        "estacionamiento_activo": estacionamiento_activo,
    })

# =========================================================
# VIEWS ADMIN
# =========================================================
@require_role("admin")
def panel_admin(request):
    usuario = request.user

    inspectores = Usuario.objects.filter(es_inspector=True, municipio=usuario.municipio)
    vendedores = Usuario.objects.filter(es_vendedor=True, municipio=usuario.municipio)
    usuarios = Usuario.objects.filter(es_conductor=True, municipio=usuario.municipio)

    rol = request.GET.get("rol")

    estacionamientos = Estacionamiento.objects.select_related(
        "vehiculo", "subcuadra", "registrado_por"
    ).filter(subcuadra__municipio=usuario.municipio)

    if rol == "vendedor":
        estacionamientos = estacionamientos.filter(registrado_por__in=vendedores)
    elif rol == "inspector":
        estacionamientos = estacionamientos.filter(registrado_por__in=inspectores)
    elif rol == "conductor":
        estacionamientos = estacionamientos.filter(registrado_por__in=usuarios)

    estacionamientos = estacionamientos.order_by("-hora_inicio")

    estacionamientos_activos = Estacionamiento.objects.filter(
        activo=True,
        subcuadra__municipio=usuario.municipio
    ).count()

    infracciones_recientes = Infraccion.objects.filter(
        subcuadra__municipio=usuario.municipio
    ).order_by('-fecha')[:5]

    return render(request, "admin/panel_admin.html", {
        "inspectores": inspectores,
        "vendedores": vendedores,
        "usuarios": usuarios,
        "estacionamientos": estacionamientos,
        "estacionamientos_activos": estacionamientos_activos,
        "infracciones_recientes": infracciones_recientes,
        "rol_seleccionado": rol,
    })

@require_role("admin")
def panel_exenciones(request):
    usuario = request.user

    vehiculo = None
    subcuadras = Subcuadra.objects.filter(municipio=usuario.municipio)

    accion = request.POST.get("accion")

    # 🔎 BUSCAR
    if request.method == "POST" and accion == "buscar":
        #patente = (input).strip().upper()
        patente = (request.POST.get('patente') or "").strip().upper()
        vehiculo = Vehiculo.objects.filter(patente=patente).first()

    # 💾 GUARDAR
    elif request.method == "POST" and accion == "guardar":
        #patente = (input).strip().upper()
        patente = (request.POST.get('patente') or "").strip().upper()
        vehiculo = Vehiculo.objects.filter(patente=patente).first()

        if vehiculo:
            vehiculo.exento_global = request.POST.get("exento_global") == "on"
            vehiculo.save()

            subcuadras_ids = request.POST.getlist("subcuadras")
            vehiculo.subcuadras_exentas.set(subcuadras_ids)

    return render(request, "admin/exenciones.html", {
        "vehiculo": vehiculo,
        "subcuadras": subcuadras
    })

@require_role("admin")
def cargar_saldo(request, usuario_id):
    admin = request.user  # quien ejecuta
    usuario = get_object_or_404(Usuario, id=usuario_id)  # a quién le cargo saldo

    if request.method == "POST":
        monto = request.POST.get("monto")
        try:
            monto = Decimal(monto)
            usuario.saldo += monto
            usuario.save()
            return redirect("panel_admin")
        except ValueError:
            return render(request, "admin/cargar_saldo.html", {
                "usuario": usuario,
                "error": "Monto inválido"
            })

    return render(request, "admin/cargar_saldo.html", {"usuario": usuario})

# =========================================================
# VIEWS USUARIOS
# =========================================================

def home(request):
    if not request.user:
        return redirect("login")

    return redirect("inicio")

def registro_view(request):
    if request.method == "POST":
        form = RegistroUsuarioForm(request.POST)

        if form.is_valid():
            usuario = form.save(commit=False)

            # 🏛️ asignar municipio
            usuario.municipio = Municipio.objects.first()

            usuario.save()

            # 🔐 LOGIN REAL DJANGO
            login(request, usuario)

            return redirect("inicio")

    else:
        form = RegistroUsuarioForm()

    return render(request, "usuarios/registro.html", {"form": form})

@require_role("conductor")
def estacionar_vehiculo(request):
    usuario = request.user

    if request.method == 'POST':
        patente = (request.POST.get('patente') or "").strip().upper()
        duracion = request.POST.get('duracion')

        vehiculo, _ = Vehiculo.objects.get_or_create(patente=patente)

        # municipio
        if not vehiculo.municipio:
            vehiculo.municipio = usuario.municipio
            vehiculo.save()

        # 🔗 relación usuario-vehiculo
        relacion, created = VehiculoUsuario.objects.get_or_create(
            usuario=usuario,
            vehiculo=vehiculo,
            defaults={
                "es_propietario": True,
                "verificado": False
            }
        )

        # 🚨 WARNING INTELIGENTE
        warning = None

        relaciones = VehiculoUsuario.objects.filter(vehiculo=vehiculo)

        propietarios = relaciones.filter(es_propietario=True)
        otros = relaciones.exclude(usuario=usuario)

        if propietarios.exists() and not propietarios.filter(usuario=usuario).exists():
            warning = "🚨 Este vehículo tiene otro propietario"

        elif otros.exists():
            warning = "⚠️ Vehículo asociado a múltiples usuarios"

        if not relacion.verificado:
            warning = (warning or "") + " | ⛔ Usuario no verificado"

        # 🔒 VALIDACIÓN PREMIUM (apagada)
        if settings.VALIDACION_ACTIVA:
            if vehiculo.exento_global or vehiculo.subcuadras_exentas.exists():
                if not relacion.verificado:
                    return render(request, 'usuarios/estacionar_vehiculo.html', {
                        'error': 'Vehículo exento requiere verificación',
                        'warning': warning
                    })

        # ❌ exento global (regla de negocio actual)
        if vehiculo.exento_global:
            return render(request, 'usuarios/estacionar_vehiculo.html', {
                'error': 'Este vehículo es exento total.',
                'warning': warning
            })

        # 🚫 doble estacionamiento
        if Estacionamiento.objects.filter(vehiculo=vehiculo, activo=True).exists():
            return render(request, 'usuarios/estacionar_vehiculo.html', {
                'error': 'El vehículo ya tiene un estacionamiento activo.',
                'warning': warning
            })

        # duración
        try:
            duracion = Decimal(duracion)
            if duracion <= 0:
                raise ValueError()
        except:
            return render(request, 'usuarios/estacionar_vehiculo.html', {
                'error': 'Duración inválida',
                'warning': warning
            })

        subcuadra = get_subcuadra_default(usuario.municipio)

        EstacionamientoFactory.crear(
            vehiculo,
            subcuadra,
            duracion,
            registrado_por=usuario
        )

        return redirect("inicio_usuarios")

    return render(request, 'usuarios/estacionar_vehiculo.html')

@require_login
def usuarios_historial(request):
    usuario = request.user

    estacionamientos = Estacionamiento.objects.filter(
        registrado_por=usuario
        ).order_by("-hora_inicio")

    return render(request, "usuarios/historial_estacionamientos.html", {
        "usuario": usuario,
        "estacionamientos": estacionamientos,
    })

@require_role("conductor")
def finalizar_estacionamiento(request, estacionamiento_id):
    usuario = request.user
    estacionamiento = get_object_or_404(Estacionamiento, id=estacionamiento_id)

    # 🔐 SOLO EL QUE LO CREÓ
    if estacionamiento.registrado_por != usuario:
        return redirect("inicio")

    # Ya finalizado
    if not estacionamiento.activo:
        return redirect("usuarios_historial_estacionamientos")

    # Calcular costo sin cerrar (preview)
    costo_estimado = estacionamiento.calcular_costo()

    # ✅ Finalizar correctamente
    costo_final = estacionamiento.finalizar()

    usuario.saldo -= costo_final
    usuario.save()

    return redirect("usuarios_historial_estacionamientos")

@require_role("conductor")
def historial_estacionamientos(request):
    usuario = request.user
    estacionamientos = Estacionamiento.objects.filter(
    vehiculo__in=usuario.vehiculos.all(),
    subcuadra__municipio=usuario.municipio
    ).order_by("-hora_inicio")
    return render(request, "usuarios/historial.html", {"estacionamientos": estacionamientos})

@require_role("inspector", "admin")
def usuarios_infracciones(request):

    usuario = request.user

    infracciones = Infraccion.objects.filter(
        municipio=usuario.municipio
    ).select_related("vehiculo", "inspector").order_by("-fecha")

    return render(request, "usuarios/historial_infracciones.html", {
        "usuario": usuario,
        "infracciones": infracciones,
    })

@require_login
def consultar_deuda(request):

    return render(request, 'usuarios/consultar_deuda.html')

# =========================================================
# VIEWS INSPECTORES
# =========================================================
@require_role("inspector", "admin")
def panel_inspectores(request):
    usuario = request.user

    if not usuario.es_inspector:
        return redirect("inicio")

    return render(request, 'inspectores/panel.html')


#    ============  en test solo @require_login   ============
#              para produccion: @require_role("inspector")

@require_login
def verificar_vehiculo(request):
    if not settings.VALIDACION_ACTIVA:
        return render(request, "inspectores/verificar_vehiculo.html", {
            "error": "Sistema en modo restringido"
        })
    usuario = request.user
    resultado = None
  
    if request.method == "POST":
        patente = (request.POST.get('patente') or "").strip().upper()

        if not patente:
            return render(request, "inspectores/verificar_vehiculo.html", {
                "error": "Debe ingresar una patente"
            })

        vehiculo, creado = Vehiculo.objects.get_or_create(patente=patente)

        # 🟢 EXENTO GLOBAL (PRIORIDAD MÁXIMA)
        if vehiculo.exento_global:
            resultado = {
                "patente": patente,
                "estado": "Exento TOTAL",
                "detalle": "Vehículo con exención total"
            }
            return render(request, "inspectores/verificar_vehiculo.html", {"resultado": resultado})

        # ❌ Vehículo no registrado
        if not vehiculo:
            resultado = {
                "patente": patente,
                "estado": "No registrado",
                "detalle": "Vehículo no registrado",
                "registrar_infraccion_url": reverse("inspectores_registrar_infraccion") + f"?patente={patente}"
            }
            return render(request, "inspectores/verificar_vehiculo.html", {"resultado": resultado})

        # 🟢 Exento global
        estacionamiento = Estacionamiento.objects.filter(
            vehiculo=vehiculo,
            activo=True,
            municipio=usuario.municipio
        ).first()

        # 🟡 Exento parcial → mostramos SIEMPRE las subcuadras
        subcuadras_exentas = vehiculo.subcuadras_exentas.all()
        
        # 🟡 Exento parcial (NO bloquea)
        if subcuadras_exentas.exists():
            resultado = {
                "patente": patente,
                "estado": "Exento parcial",
                "subcuadras_exentas": subcuadras_exentas,
                "detalle": "Puede estar exento según la subcuadra"
            }
        
            # 👉 SI NO tiene estacionamiento → puede multar
            if not estacionamiento:
                resultado["registrar_infraccion_url"] = reverse("inspectores_registrar_infraccion") + f"?patente={patente}"
        
            # 👉 SI tiene estacionamiento activo → no multa
            else:
                resultado["detalle"] = "Tiene estacionamiento activo"
        
            return render(request, "inspectores/verificar_vehiculo.html", {"resultado": resultado})

        # 🟢 Pagado (activo)
        if estacionamiento and estacionamiento.activo:
            resultado = {
                "patente": patente,
                "estado": "Pagado",
                "detalle": "Estacionamiento activo"
            }
            return render(request, "inspectores/verificar_vehiculo.html", {"resultado": resultado})

        # 🔴 Impago
        resultado = {
            "patente": patente,
            "estado": "Impago",
            "detalle": "Estacionamiento sin pago",
            "registrar_infraccion_url": reverse("inspectores_registrar_infraccion") + f"?patente={patente}"
        }

        return render(request, "inspectores/verificar_vehiculo.html", {"resultado": resultado})

    return render(request, "inspectores/verificar_vehiculo.html")

@require_role("inspector")
def registrar_infraccion(request):
    usuario = request.user
    mensaje = None

    subcuadras = Subcuadra.objects.filter(municipio=usuario.municipio)
    #patente = (input).strip().upper()
    patente = (request.GET.get("patente") or request.POST.get("patente") or "").strip().upper()

    if request.method == "POST":
        subcuadra_id = request.POST.get("subcuadra_id")
        foto = request.FILES.get("foto")

        subcuadra = Subcuadra.objects.filter(
            id=subcuadra_id,
            municipio=usuario.municipio
        ).first()

        vehiculo, creado = Vehiculo.objects.get_or_create(patente=patente)

        estacionamiento = Estacionamiento.objects.filter(
            vehiculo=vehiculo,
            activo=True,
            municipio=usuario.municipio
        ).order_by("-hora_inicio").first()

        if not vehiculo:
            mensaje = "❌ Vehículo inexistente"

        elif not subcuadra:
            mensaje = "❌ Subcuadra inválida"

        elif vehiculo.exento_global:
            mensaje = "🚫 Exento TOTAL"

        elif vehiculo.esta_exento_en(subcuadra):
            mensaje = "🚫 Exento en esta subcuadra - No multa"

        elif estacionamiento and estacionamiento.activo:
            mensaje = "🚫 Tiene estacionamiento activo (no se multa)"

        else:

            inf = Infraccion.objects.create(
                vehiculo=vehiculo,
                inspector=usuario,
                municipio=usuario.municipio,
                subcuadra=subcuadra,
                estacionamiento=estacionamiento,
                foto=foto
            )

            mensaje = f"🚨 Infracción registrada para {patente}"

    return render(request, "inspectores/registrar_infraccion.html", {
        "mensaje": mensaje,
        "subcuadras": subcuadras,
        "patente": patente,
    })

@require_role("inspector", "admin", "vendedor")
def registrar_estacionamiento_manual(request):
    inspector = request.user

    if request.method == "POST":
        #patente = (input).strip().upper()
        patente = (request.POST.get('patente') or "").strip().upper()
        duracion = request.POST.get("duracion")

        vehiculo, _ = Vehiculo.objects.get_or_create(patente=patente)

        if Estacionamiento.objects.filter(vehiculo=vehiculo, activo=True).exists():
            return render(request, "inspectores/registrar_estacionamiento_manual.html", {
                "error": "El vehículo ya tiene un estacionamiento activo."
            })

        try:
            duracion = Decimal(duracion)
            if duracion <= 0 or duracion % 1 != 0:
                raise ValueError()
        except:
            return render(request, "inspectores/registrar_estacionamiento_manual.html", {
                "error": "La duración debe ser en horas (ej: 1, 2)."
            })

        subcuadra = get_subcuadra_default(inspector.municipio)
        EstacionamientoFactory.crear(vehiculo, subcuadra, duracion, registrado_por=inspector)

        return redirect("inspectores_verificar_vehiculo")

    return render(request, "inspectores/registrar_estacionamiento_manual.html")

@require_role("vendedor")
def registrar_estacionamiento_vendedor(request):
    vendedor = request.user

    if request.method == "POST":
        #patente = (input).strip().upper()
        patente = (request.POST.get('patente') or "").strip().upper()
        duracion = request.POST.get("duracion")
        cliente_email = request.POST.get("cliente_email", "").strip()

        # Buscar o crear vehículo
        vehiculo, _ = Vehiculo.objects.get_or_create(patente=patente)

        # Asociar vehículo al cliente (si existe y si es ManyToMany)
        if cliente_email:
            cliente = Usuario.objects.filter(correo=cliente_email).first()
            if cliente:
                # si la relación es ManyToMany
                if hasattr(cliente, "vehiculos"):
                    cliente.vehiculos.add(vehiculo)

        # Validar que no tenga estacionamiento activo
        if Estacionamiento.objects.filter(vehiculo=vehiculo, activo=True).exists():
            return render(request, "vendedores/registrar_estacionamiento.html", {
                "error": "El vehículo ya tiene un estacionamiento activo."
            })

        # Validar duración (múltiplos de 1 hora; usa (duracion*2)%1 != 0 si querés medias horas)
        try:
            duracion = Decimal(duracion)
            if duracion <= 0 or duracion % 1 != 0:
                raise ValueError("Duración inválida")
        except Exception:
            return render(request, "vendedores/registrar_estacionamiento.html", {
                "error": "La duración debe ser en pasos de horas (ej: 1, 2)."
            })

        # Subcuadra única
        subcuadra = get_subcuadra_default(vendedor.municipio)

        # Crear estacionamiento
        EstacionamientoFactory.crear(vehiculo, subcuadra, duracion, registrado_por=vendedor)

        return redirect("vendedores_resumen_caja")

    return render(request, "vendedores/registrar_estacionamiento.html")

@require_role("inspector", "vendedor", "admin")
def resumen_cobros(request):
    usuario = request.user

    if not usuario.es_inspector:
        return redirect("inicio")

    return render(request, 'inspectores/resumen_cobros.html')

@require_role("inspector", "admin")
def resumen_infracciones(request):
    usuario = request.user

    infracciones = Infraccion.objects.filter(
        municipio=usuario.municipio
    ).select_related("vehiculo", "subcuadra").order_by("-fecha")

    return render(request, "inspectores/resumen_infracciones.html", {
        "infracciones": infracciones
    })

# =========================================================
# VIEWS VENDEDORES
# =========================================================
@require_role("vendedor", "admin")
def panel_vendedores(request):
    """
    Panel principal de vendedores.
    - Solo accesible a vendedores.
    """
    usuario = request.user
    if not usuario.es_vendedor:
        return redirect("inicio")
    return render(request, 'vendedores/panel.html', {"vendedor": usuario})

@require_role("vendedor", "admin")
def resumen_caja(request):
    usuario = request.user

    registros = Estacionamiento.objects.filter(registrado_por=usuario).order_by("-hora_inicio")

    return render(request, 'vendedores/resumen_caja.html', {"registros": registros})

# =========================================================
# VIEWS LOGIN / LOGOUT

def logout_view(request):
    logout(request)
    return redirect("login")