# Análisis para Google AI Studio — Sistema de Estacionamiento Medido
Fecha: 2026-09-06

---

## ══ PROMPT PARA AI STUDIO ══

Copia este texto como prompt, y adjuntá este mismo archivo como contexto:

---

Sos un ingeniero senior full-stack y experto en UX/UI. Voy a mostrarte 4 funcionalidades recién implementadas en mi sistema Django + HTML/CSS (sin frameworks JS, sin Tailwind, CSS propio). Quiero que analices cada una y me des sugerencias concretas de mejora en dos ejes:

1. **Código / arquitectura**: ¿hay algo mejorable en la lógica, seguridad, mantenibilidad o escalabilidad?
2. **UX/UI**: ¿la pantalla es clara, previene errores, comunica bien los estados? ¿Qué cambiarías?

Para cada ítem usá este formato:

```
## [Nombre del ítem]
### Problemas detectados
- [problema 1]
- [problema 2]
### Sugerencias concretas
- [sugerencia 1 con código o descripción precisa]
- [sugerencia 2]
### Prioridad sugerida
🔴 Alta / 🟡 Media / 🟢 Baja — [justificación]
```

Al final agregá una sección `## UX/UI global` con observaciones transversales a todos los formularios y pantallas del sistema (no solo los 4 ítems).

El contexto completo del sistema y el código de cada ítem están en el archivo adjunto.

---

## ══ CONTEXTO DEL SISTEMA ══

### Stack
- Django 5.2, Python 3.12
- Frontend: HTML + CSS propio (`global.css`). Sin frameworks JS. Sin Tailwind.
- Base de datos: SQLite local / PostgreSQL en Railway
- Multi-tenant: cada municipio tiene sus propios datos, usuarios, configuración y colores

### Roles
| Rol | Descripción |
|-----|-------------|
| conductor | Ciudadano que estaciona |
| inspector | Labra infracciones en la calle |
| vendedor | Cobra estacionamientos en efectivo |
| admin | Administra un municipio |
| tesorero | Gestiona liquidaciones y caja |
| superadmin | Controla todos los municipios |

### Filosofía de código
- Nombres en castellano, funciones separadas, sin sobreingeniería
- Sin dependencias innecesarias
- CSS en un único archivo global; los templates no tienen `<style>` inline salvo casos muy puntuales

---

## ══ ÍTEM 1: Reseteo de contraseña para admins ══

**Descripción:** El admin de un municipio puede resetear la contraseña de otros admins o tesoreros de su mismo municipio desde su panel. La contraseña es temporal; el usuario afectado debe cambiarla al próximo login (`cambio_password_requerido=True`).

### Vista (views_admin.py — función editar_staff)

```python
@require_role("admin")
def editar_staff(request, usuario_id):
    """
    El admin puede:
      - Ver y editar datos de un admin o tesorero de su municipio
      - Resetear la contraseña (temporal, fuerza cambio en próximo login)
      - Activar / desactivar la cuenta
    No puede editar su propio usuario desde acá (evita bloqueo accidental).
    """
    municipio = request.user.municipio
    staff = get_object_or_404(
        Usuario,
        id=usuario_id,
        municipio=municipio,
    )
    if not (staff.es_admin or staff.es_tesorero):
        messages.error(request, "Solo podés editar admins o tesoreros.")
        return redirect("gestionar_staff")
    if staff.pk == request.user.pk:
        messages.error(request, "No podés editarte a vos mismo desde acá.")
        return redirect("gestionar_staff")

    if request.method == "POST":
        accion = request.POST.get("accion", "editar")

        if accion == "editar":
            staff.first_name = request.POST.get("first_name", "").strip()
            staff.last_name  = request.POST.get("last_name", "").strip()
            staff.telefono   = request.POST.get("telefono", "").strip()
            staff.is_active  = request.POST.get("is_active") == "on"
            staff.save(update_fields=["first_name", "last_name", "telefono", "is_active"])
            messages.success(request, "Datos actualizados.")

        elif accion == "cambiar_password":
            nueva    = request.POST.get("nueva_password", "").strip()
            confirma = request.POST.get("confirmar_password", "").strip()
            if not nueva:
                messages.error(request, "La contraseña no puede estar vacía.")
            elif nueva != confirma:
                messages.error(request, "Las contraseñas no coinciden.")
            elif len(nueva) < 6:
                messages.error(request, "Mínimo 6 caracteres.")
            else:
                staff.set_password(nueva)
                staff.cambio_password_requerido = True
                staff.save()
                messages.success(
                    request,
                    f"Contraseña temporal establecida para {staff.correo}. "
                    "Deberá cambiarla en el próximo login."
                )

        return redirect("editar_staff", usuario_id=staff.pk)

    return render(request, "admin/editar_staff.html", {
        "staff": staff,
    })
```

### Template (admin/editar_staff.html)

```html
{% extends "base.html" %}
{% block content %}
<div class="container" style="max-width:620px; margin:2rem auto;">

  <a href="{% url 'gestionar_staff' %}">← Volver</a>
  <h2>{% if staff.es_admin %}🏛️ Admin{% else %}💳 Tesorero{% endif %} — {{ staff.correo }}</h2>

  {% include "components/messages.html" %}

  <!-- Datos generales -->
  <section style="background:var(--color-bg-alt,#f9f9f9); border:1px solid #ddd;
                  border-radius:8px; padding:1.2rem; margin-bottom:1.2rem;">
    <h3>Datos generales</h3>
    <form method="post">
      {% csrf_token %}
      <input type="hidden" name="accion" value="editar">
      <div style="display:flex; gap:.8rem; flex-wrap:wrap; margin-bottom:.7rem;">
        <div style="flex:1; min-width:160px;">
          <label>Nombre</label>
          <input type="text" name="first_name" value="{{ staff.first_name }}" style="width:100%; ...">
        </div>
        <div style="flex:1; min-width:160px;">
          <label>Apellido</label>
          <input type="text" name="last_name" value="{{ staff.last_name }}" style="width:100%; ...">
        </div>
      </div>
      <div>
        <label>Teléfono</label>
        <input type="text" name="telefono" value="{{ staff.telefono|default:'' }}" style="width:100%; ...">
      </div>
      <label>
        <input type="checkbox" name="is_active" {% if staff.is_active %}checked{% endif %}>
        Cuenta activa
      </label>
      <button type="submit">Guardar cambios</button>
    </form>
  </section>

  <!-- Cambio de contraseña -->
  <section style="background:var(--color-bg-alt,#f9f9f9); border:1px solid #ddd;
                  border-radius:8px; padding:1.2rem;">
    <h3>🔑 Resetear contraseña</h3>
    <p>La contraseña que establezcas es temporal.
       {{ staff.correo }} deberá cambiarla en el próximo login.
       Comunicásela por fuera del sistema.</p>
    <form method="post">
      {% csrf_token %}
      <input type="hidden" name="accion" value="cambiar_password">
      <div style="display:flex; gap:.8rem; flex-wrap:wrap; margin-bottom:.7rem;">
        <div style="flex:1; min-width:180px;">
          <label>Nueva contraseña</label>
          <input type="text" name="nueva_password" minlength="6" required style="width:100%; ...">
        </div>
        <div style="flex:1; min-width:180px;">
          <label>Confirmar</label>
          <input type="text" name="confirmar_password" minlength="6" required style="width:100%; ...">
        </div>
      </div>
      <button type="submit"
        onclick="return confirm('¿Establecer contraseña temporal para {{ staff.correo }}?')">
        Establecer contraseña temporal
      </button>
    </form>
  </section>
</div>
{% endblock %}
```

### Notas de diseño
- La contraseña nueva se muestra en `type="text"` (no `type="password"`) porque el admin la va a comunicar por WhatsApp/teléfono y necesita verla.
- El confirm() de JS es el único mecanismo de confirmación ante una acción irreversible (desautoriza la sesión activa del usuario afectado).
- No hay log/auditoría del cambio de contraseña más allá de `cambio_password_requerido=True`.

---

## ══ ÍTEM 2: Sectorizar editar_municipio ══

**Descripción:** El formulario de edición de municipio del superadmin tenía un único `<form>` grande con todos los campos mezclados. Se dividió en 4 secciones independientes, cada una con su propio botón "Guardar". Así el superadmin puede guardar solo la parte que editó sin afectar las otras.

### Vista (views_superadmin.py — función editar_municipio, sección POST)

```python
@require_role("superadmin")
def editar_municipio(request, municipio_id):
    municipio = get_object_or_404(Municipio, id=municipio_id)

    if request.method == "POST":
        accion = request.POST.get("accion", "")

        # ── Acciones especiales (sin cambio de sección) ──
        if accion == "toggle_activo":
            municipio.activo = not municipio.activo
            municipio.save(update_fields=["activo"])
            estado = "activado" if municipio.activo else "desactivado"
            messages.success(request, f"Municipio {estado}.")
            return redirect("editar_municipio", municipio_id=municipio.id)

        if accion == "generar_token_tv":
            import secrets
            municipio.token_tv = secrets.token_urlsafe(32)
            municipio.save(update_fields=["token_tv"])
            messages.success(request, "Token TV regenerado.")
            return redirect("editar_municipio", municipio_id=municipio.id)

        if accion == "limpiar_datos_prueba":
            # borra todos los datos de prueba del municipio
            ...
            return redirect("editar_municipio", municipio_id=municipio.id)

        # ── Sección 1: Configuración general ──
        if accion in ("guardar_general", ""):
            municipio.nombre                      = request.POST.get("nombre", municipio.nombre).strip()
            municipio.nombre_sistema              = request.POST.get("nombre_sistema", "").strip()
            municipio.monto_minimo_carga          = request.POST.get("monto_minimo_carga") or municipio.monto_minimo_carga
            municipio.monto_maximo_carga          = request.POST.get("monto_maximo_carga") or municipio.monto_maximo_carga
            municipio.minutos_entre_infracciones  = request.POST.get("minutos_entre_infracciones") or municipio.minutos_entre_infracciones
            municipio.activo                      = request.POST.get("activo") == "on"
            municipio.reintegro_activo            = request.POST.get("reintegro_activo") == "on"
            municipio.reintegro_porcentaje        = request.POST.get("reintegro_porcentaje") or municipio.reintegro_porcentaje
            municipio.reintegro_plazo_dias        = request.POST.get("reintegro_plazo_dias") or municipio.reintegro_plazo_dias
            municipio.save()
            messages.success(request, "Configuración general guardada.")
            return redirect("editar_municipio", municipio_id=municipio.id)

        # ── Sección 2: Facturación ──
        if accion == "guardar_facturacion":
            municipio.cuota_mantenimiento_mensual = request.POST.get("cuota_mantenimiento_mensual") or municipio.cuota_mantenimiento_mensual
            municipio.porcentaje_plataforma       = request.POST.get("porcentaje_plataforma") or municipio.porcentaje_plataforma
            municipio.dia_cierre_liquidacion      = request.POST.get("dia_cierre_liquidacion") or municipio.dia_cierre_liquidacion
            municipio.concepto_recaudacion        = request.POST.get("concepto_recaudacion", "").strip()
            municipio.save()
            messages.success(request, "Facturación guardada.")
            return redirect("editar_municipio", municipio_id=municipio.id)

        # ── Sección 3: Institucional ──
        if accion == "guardar_institucional":
            municipio.leyenda_horarios  = request.POST.get("leyenda_horarios", "").strip()
            municipio.texto_ordenanza   = request.POST.get("texto_ordenanza", "").strip()
            municipio.save()
            messages.success(request, "Información institucional guardada.")
            return redirect("editar_municipio", municipio_id=municipio.id)

        # ── Sección 4: Branding / identidad visual ──
        if accion == "guardar_branding":
            municipio.color_primario   = request.POST.get("color_primario", municipio.color_primario)
            municipio.color_secundario = request.POST.get("color_secundario", municipio.color_secundario)
            municipio.color_acento     = request.POST.get("color_acento", municipio.color_acento)
            if "logo" in request.FILES:
                municipio.logo = request.FILES["logo"]
            if "icono_app" in request.FILES:
                municipio.icono_app = request.FILES["icono_app"]
            municipio.save()
            messages.success(request, "Identidad visual guardada.")
            return redirect("editar_municipio", municipio_id=municipio.id)

    return render(request, "superadmin/editar_municipio.html", {"municipio": municipio})
```

### Template (estructura resumida — superadmin/editar_municipio.html)

```html
<!-- SECCIÓN 1: Configuración general -->
<form method="post">
  {% csrf_token %}
  <input type="hidden" name="accion" value="guardar_general">
  <!-- campos: nombre, nombre_sistema, montos, minutos_entre_infracciones,
               activo (checkbox), reintegro_activo, reintegro_porcentaje, reintegro_plazo_dias -->
  <button type="submit">💾 Guardar configuración general</button>
</form>

<!-- SECCIÓN 2: Facturación -->
<form method="post">
  {% csrf_token %}
  <input type="hidden" name="accion" value="guardar_facturacion">
  <!-- campos: cuota_mantenimiento_mensual, porcentaje_plataforma,
               dia_cierre_liquidacion, concepto_recaudacion -->
  <button type="submit">💾 Guardar facturación</button>
</form>

<!-- SECCIÓN 3: Institucional -->
<form method="post">
  {% csrf_token %}
  <input type="hidden" name="accion" value="guardar_institucional">
  <!-- campos: leyenda_horarios (textarea), texto_ordenanza (textarea) -->
  <button type="submit">💾 Guardar información institucional</button>
</form>

<!-- SECCIÓN 4: Branding / identidad visual -->
<form method="post" enctype="multipart/form-data">
  {% csrf_token %}
  <input type="hidden" name="accion" value="guardar_branding">
  <!-- campos: color_primario, color_secundario, color_acento (color inputs),
               logo (file), icono_app (file) -->
  <button type="submit">💾 Guardar identidad visual</button>
</form>
```

### Notas de diseño
- Antes había un único form grande. Guardar Sección 1 no debería tocar los campos de branding ni facturación.
- El `accion in ("guardar_general", "")` es un fallback para el caso de que no venga accion en el POST.
- El redirect vuelve a `editar_municipio` (no al panel) para que el superadmin siga editando otras secciones.
- No hay indicación visual de qué sección está "sin guardar" si el usuario hace cambios en varias y olvida guardar alguna.

---

## ══ ÍTEM 3: Admin puede gestionar tesoreros ══

**Descripción:** Antes, solo el superadmin podía crear tesoreros. Ahora el admin de un municipio puede crear nuevos tesoreros para su propio municipio, activarlos/desactivarlos y resetear sus contraseñas. No puede crear otros admins (solo el superadmin puede).

### Vista (views_admin.py — función gestionar_staff)

```python
@require_role("admin")
def gestionar_staff(request):
    """
    Lista los admins y tesoreros del municipio.
    El admin puede crear nuevos tesoreros y resetear contraseñas de ambos roles.
    """
    municipio = request.user.municipio
    admins    = Usuario.objects.filter(municipio=municipio, es_admin=True).order_by("-is_active", "correo")
    tesoreros = Usuario.objects.filter(municipio=municipio, es_tesorero=True).order_by("-is_active", "correo")

    if request.method == "POST":
        accion = request.POST.get("accion", "")

        if accion == "crear_tesorero":
            correo   = request.POST.get("correo", "").strip().lower()
            nombre   = request.POST.get("first_name", "").strip()
            apellido = request.POST.get("last_name", "").strip()
            password = request.POST.get("password", "").strip()

            if not correo or not nombre or not password:
                messages.error(request, "Completá todos los campos obligatorios.")
            elif len(password) < 6:
                messages.error(request, "La contraseña debe tener al menos 6 caracteres.")
            elif Usuario.objects.filter(correo=correo).exists():
                messages.error(request, f"Ya existe un usuario con el correo {correo}.")
            else:
                from django.contrib.auth.hashers import make_password
                Usuario.objects.create(
                    correo=correo,
                    username=correo,
                    first_name=nombre,
                    last_name=apellido,
                    password=make_password(password),
                    municipio=municipio,
                    es_tesorero=True,
                    es_conductor=False,
                    is_active=True,
                    cambio_password_requerido=True,
                )
                messages.success(request, f"Tesorero {correo} creado. Debe cambiar su contraseña al primer login.")
            return redirect("gestionar_staff")

    return render(request, "admin/gestionar_staff.html", {
        "admins":    admins,
        "tesoreros": tesoreros,
        "municipio": municipio,
    })
```

### Template (admin/gestionar_staff.html — estructura resumida)

```html
<h2>👥 Administradores y tesoreros — {{ municipio.nombre }}</h2>

<!-- Tabla de admins (solo lectura para el propio admin; otros con link "Editar →") -->
<h3>🏛️ Administradores</h3>
<table>
  {% for u in admins %}
    <tr>
      <td>{{ u.nombre_completo }}</td>
      <td>{{ u.correo }}</td>
      <td>{% if u.is_active %}✅ Activo{% else %}❌ Inactivo{% endif %}</td>
      <td>
        {% if u.pk != request.user.pk %}
          <a href="{% url 'editar_staff' u.pk %}">Editar →</a>
        {% else %}
          (vos)
        {% endif %}
      </td>
    </tr>
  {% endfor %}
</table>

<!-- Botón que despliega el formulario de nuevo tesorero (oculto por defecto) -->
<button onclick="document.getElementById('form-nuevo-tesorero').style.display='block'; this.style.display='none';">
  + Nuevo tesorero
</button>

<div id="form-nuevo-tesorero" style="display:none;">
  <form method="post">
    {% csrf_token %}
    <input type="hidden" name="accion" value="crear_tesorero">
    <!-- campos: first_name, last_name, correo, password (tipo text) -->
    <button type="submit">Crear tesorero</button>
    <button type="button" onclick="document.getElementById('form-nuevo-tesorero').style.display='none';">Cancelar</button>
  </form>
</div>

<!-- Tabla de tesoreros (con link "Editar →" para todos) -->
<h3>💳 Tesoreros</h3>
<table>
  {% for u in tesoreros %}
    <tr>
      <td>{{ u.nombre_completo }}</td>
      <td>{{ u.correo }}</td>
      <td>{% if u.is_active %}✅ Activo{% else %}❌ Inactivo{% endif %}</td>
      <td><a href="{% url 'editar_staff' u.pk %}">Editar →</a></td>
    </tr>
  {% endfor %}
</table>
```

### Notas de diseño
- La contraseña inicial se muestra en `type="text"` (el admin la va a comunicar fuera del sistema).
- El admin puede editar admins de su mismo municipio (resetear contraseña, activar/desactivar), pero no puede crear más admins.
- El formulario de "nuevo tesorero" se muestra/oculta con JS inline (`display:none/block`), sin ningún framework.
- No hay validación del formato del correo en el backend (se delega a `type="email"` del HTML).

---

## ══ ÍTEM 4: Responsive ≥ 1050px ══

**Descripción:** En pantallas anchas (desktop), el contenido quedaba estirado al 100% del ancho sin tope. Se agregó un bloque `@media (min-width: 1050px)` en `global.css` que limita el ancho máximo y asegura que los grids y la navbar se comporten correctamente.

### CSS agregado (global.css — al final del archivo)

```css
/* ─── RESPONSIVE — DESKTOP ANCHO (≥ 1050px) ─────────────────── */
@media (min-width: 1050px) {

  /* Limitar el ancho máximo del contenido para no estirar en pantallas muy anchas.
     El container ya tiene padding lateral; acá solo lo centramos y le ponemos techo. */
  .container {
    max-width: 1280px;
    margin-left: auto;
    margin-right: auto;
  }

  /* Cuando el container está dentro de main.container (casi siempre),
     heredamos el centrado sin doble margen. */
  main.container > .container {
    max-width: 1280px;
  }

  /* Navbar: mostrar ítems horizontalmente */
  .menu-toggle { display: none !important; }
  .nav-items {
    position: static;
    flex-direction: row;
    height: auto;
    width: auto;
    padding: 0;
    box-shadow: none;
    background: transparent;
    overflow-y: visible;
  }

  /* Grids a 2/3/4 columnas según clase */
  .grid-2 { grid-template-columns: repeat(2, 1fr); }
  .grid-3 { grid-template-columns: repeat(3, 1fr); }
  .grid-4 { grid-template-columns: repeat(4, 1fr); }

  /* Cards: quitamos el overflow-x:auto que se aplica en mobile
     para que los dropdowns no queden cortados en desktop. */
  .card { overflow-x: visible; }
}
```

### Notas de diseño
- La estrategia fue mobile-first desde el inicio, así que el `@media (min-width: ...)` es un override encima de lo que ya existe.
- Los templates individuales usan inline `style="max-width:Xpx"` en algunos containers específicos (ej. formularios de 620px de ancho). Ese inline tiene mayor especificidad que la clase `.container`, así que ya están bien limitados sin que el @media los afecte.
- No hay breakpoints intermedios (768px, 992px) — fue una decisión deliberada de simplificar. El sistema se usa principalmente en mobile (inspectores en la calle) o en desktop (panel admin). La zona "tablet" no es prioritaria.
- El bloque no resuelve el caso de tablas de muchas columnas en desktop que siguen siendo `overflow-x:auto`.

---

## ══ CONTEXTO UX/UI ADICIONAL ══

### Convenciones visuales del sistema
- CSS variables: `--color-primary`, `--color-secondary`, `--color-acento` (inyectadas desde los colores del municipio)
- Clases de utilidad: `.container`, `.card`, `.grid-2/3/4`, `.btn`, `.btn-outline`, `.alert`, `.alert-success/warning/danger`
- Dark mode: `data-theme="dark"` en `<html>`, con overrides explícitos en `global.css`
- Emojis como indicadores de estado/tipo (✅ activo, ❌ inactivo, 🔴 crítico, etc.)

### Pantallas que más usa cada rol
- **Inspector**: `verificar_vehiculo` (en la calle, celular, sol, guantes) → botones grandes, flujo rápido
- **Admin**: dashboard con KPIs, lista de infracciones, gestión de staff
- **Conductor**: inicio con saldo y vehículos, estacionar, historial
- **Superadmin**: editar_municipio (el más complejo), panel de sugerencias

### Problemas conocidos / deuda UX
- Los templates tienen mucho `style=""` inline mezclado con clases CSS (inconsistencia acumulada)
- No hay un sistema de componentes: cada sección de formulario se construye con HTML repetido a mano
- El estado "guardando" no existe: el botón submit se deshabilita con JS en base.html, pero no hay spinner ni indicación visual de progreso
- Los mensajes de Django (`messages.success/error`) aparecen todos arriba del contenido, sin asociarse al campo o sección que los generó
- El sistema de roles es por flags booleanos en el modelo (`es_admin`, `es_inspector`, etc.), no por grupos de Django
