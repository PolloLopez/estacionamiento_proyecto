# Auditoría Completa — Sistema de Estacionamiento
**Fecha:** 2026-06-06  
**Versión analizada:** branch `main` / tag `v0.7-tests-estables`  
**Stack:** Django 5.2, SQLite, Python 3.12

---

## Índice

1. [Resumen ejecutivo](#1-resumen-ejecutivo)
2. [Bugs críticos](#2-bugs-críticos)
3. [Seguridad](#3-seguridad)
4. [Trazabilidad y auditoría](#4-trazabilidad-y-auditoría)
5. [UX/UI — Conductores](#5-uxui--conductores)
6. [UX/UI — Inspectores](#6-uxui--inspectores)
7. [Gestión de usuarios, inspectores y vendedores](#7-gestión-de-usuarios-inspectores-y-vendedores)
8. [Arquitectura (ADR)](#8-arquitectura-adr)
9. [Documentación](#9-documentación)
10. [Estrategia de testing](#10-estrategia-de-testing)
11. [Roadmap de correcciones priorizadas](#11-roadmap-de-correcciones-priorizadas)

---

## 1. Resumen ejecutivo

El sistema tiene una base arquitectónica sana: capas separadas (views → use cases → services → domain), modelos bien tipados, tests automatizados y lógica de negocio desacoplada de Django. Sin embargo, la auditoría encontró **problemas que bloquean producción**, incluyendo vistas sin protección de roles, lógica de pago duplicada e inconsistente, templates referenciadas que no existen y campos de fecha redundantes que dificultan cualquier auditoría contable.

**Clasificación de hallazgos:**

| Severidad | Cantidad |
|-----------|---------|
| 🔴 Crítico | 9 |
| 🟠 Alto | 11 |
| 🟡 Medio | 8 |
| 🔵 Bajo | 5 |

---

## 2. Bugs críticos

### 2.1 — `Estacionamiento.Meta` fuera de la clase
**Archivo:** `models.py`

```python
class Estacionamiento(models.Model):
    ...
    @property
    def activo(self):
        return self.estado == Estado.ACTIVO

class Meta:   # ← está a nivel módulo, no dentro de Estacionamiento
    constraints = [...]
```

El constraint `unique_estacionamiento_activo_por_vehiculo` nunca se aplica. Un vehículo puede tener múltiples estacionamientos activos simultáneos.

**Corrección:**
```python
class Estacionamiento(models.Model):
    ...
    @property
    def activo(self):
        return self.estado == Estado.ACTIVO

    class Meta:   # ← adentro
        constraints = [
            UniqueConstraint(
                fields=["vehiculo"],
                condition=Q(estado="ACTIVO"),
                name="unique_estacionamiento_activo_por_vehiculo",
            )
        ]
```

---

### 2.2 — Imports incorrectos en `views.py`
**Archivo:** `views.py` (primeras líneas)

```python
from pyexpat.errors import messages      # ← INCORRECTO
from unittest import result              # ← no se usa
from urllib import request               # ← no se usa
from django_extensions import models     # ← incorrecto, no se usa
```

`messages` nunca funciona en todo el sistema porque está importado del módulo equivocado. Las llamadas a `messages.success()` y `messages.error()` en views silenciosamente no hacen nada.

**Corrección:**
```python
from django.contrib import messages
```

---

### 2.3 — Templates que no existen
Las siguientes vistas renderizan templates inexistentes, produciendo un `TemplateDoesNotExist` en producción:

| Vista | Template referenciada | Template real |
|---|---|---|
| `mis_infracciones` | `usuarios/mis_infracciones.html` | `usuarios/historial_infracciones.html` |
| `agregar_vehiculo` | `usuarios/agregar_vehiculo.html` | No existe |
| `dashboard_admin` | `admin/dashboard.html` | No existe |
| `ticket_cobro` | usa `est.duracion` | Campo es `duracion_min` |

---

### 2.4 — `pagar_infraccion` en views no usa el use case
**Archivo:** `views.py` → `pagar_infraccion()`

La view marca la infracción como pagada directamente sin:
- Verificar saldo del conductor
- Descontar saldo
- Registrar movimiento de caja
- Usar `select_for_update` (race condition)

El use case correcto existe en `use_cases/pagar_infraccion.py` pero nunca se llama.

**Corrección:**
```python
from app_estacionamiento.use_cases.pagar_infraccion import ejecutar as pagar_infraccion_uc

@require_role("admin","inspector","vendedor")
def pagar_infraccion(request, infraccion_id):
    infraccion = get_object_or_404(Infraccion, id=infraccion_id)
    try:
        pagar_infraccion_uc(request.user, infraccion)
        messages.success(request, "Infracción cobrada.")
    except Exception as e:
        messages.error(request, str(e))
    return redirect("gestion_infracciones")
```

---

### 2.5 — `simular_pago` sin protección de rol
**Archivo:** `views.py` → `simular_pago()`

```python
def simular_pago(request, infraccion_id):   # ← sin @require_role
    infraccion = Infraccion.objects.get(id=infraccion_id)
    infraccion.estado = "pagado"   # ← además el valor es "pagado" no "pagada"
    infraccion.save()
```

Cualquier usuario anónimo puede marcar una infracción como pagada accediendo a la URL directamente.

---

### 2.6 — `cerrar_caja` sin protección de rol
**Archivo:** `views.py` → `cerrar_caja()`

```python
def cerrar_caja(request):   # ← sin @require_role ni @require_login
```

Cualquier usuario puede disparar un cierre de caja, incluso usuarios no autenticados.

---

### 2.7 — `panel_exenciones` lanza `NameError`
**Archivo:** `views.py` → `panel_exenciones()`

```python
def panel_exenciones(request):
    ...
    # Si request.method == "GET", 'vehiculo' nunca se define
    return render(request, "admin/exenciones.html", {
        "vehiculo": vehiculo,   # ← NameError en GET
        ...
    })
```

**Corrección:**
```python
vehiculo = None
if request.method == "POST" and accion == "buscar":
    ...
```

---

### 2.8 — `registrar_estacionamiento_manual` no crea `Estacionamiento`
**Archivo:** `views.py` → `registrar_estacionamiento_manual()`

La vista cobra y registra un `MovimientoCaja`, pero **nunca crea un `Estacionamiento`**. Si después el inspector verifica el vehículo, aparecerá como impago y generará una infracción errónea.

Además usa `TARIFA = Decimal("100")` hardcodeado, ignorando el modelo `Tarifa`.

---

### 2.9 — Lógica de tolerancia rota en `verificar_estado_vehiculo`
**Archivo:** `services_verificacion.py`

```python
# Primero registra la verificación actual...
VerificacionInspector.objects.create(vehiculo=vehiculo, ...)

# ...luego busca la SEGUNDA verificación para calcular tolerancia
ultima_verificacion = VerificacionInspector.objects.filter(
    vehiculo=vehiculo
).order_by("-fecha")[1:2].first()   # ← salta la que acaba de crear
```

La lógica intenta omitir la verificación recién creada tomando el índice `[1:2]`, pero esto hace que la tolerancia se calcule contra la verificación anterior al inspector actual, no la del mismo turno. Si el mismo inspector verifica dos veces en menos de 15 minutos, la segunda vez verá `PENDIENTE_PAGO` aunque el vehículo sea impago desde hace horas.

---

## 3. Seguridad

### 3.1 — `SECRET_KEY` con fallback inseguro
**Archivo:** `settings.py`

```python
SECRET_KEY = os.getenv("SECRET_KEY", "dev-key")
```

Si `SECRET_KEY` no está en el entorno (lo cual ocurre en cualquier deploy descuidado), se usa `"dev-key"`. Esto compromete todas las sesiones y tokens CSRF.

**Corrección:**
```python
SECRET_KEY = os.environ["SECRET_KEY"]   # falla duro si no está
```

### 3.2 — `DEBUG = True` y `ALLOWED_HOSTS = ["*"]` hardcodeados
No hay separación de configuración dev/prod. En producción se debe usar variables de entorno o archivos de settings separados.

### 3.3 — Sin validadores de contraseña
```python
AUTH_PASSWORD_VALIDATORS = []   # ← vacío
```
Permite contraseñas de 1 carácter. Agregar al menos `MinimumLengthValidator` y `CommonPasswordValidator`.

### 3.4 — `resumen_cobros` devuelve datos de todos los municipios
```python
def resumen_cobros(request):
    cobros = MovimientoCaja.objects.all()   # ← sin filtro por municipio
```
Un inspector de un municipio puede ver los cobros de otro.

---

## 4. Trazabilidad y auditoría

### 4.1 — `Infraccion` tiene 4 campos de fecha redundantes

```python
class Infraccion(models.Model):
    fecha_creacion = models.DateTimeField(auto_now_add=True, null=True)
    fecha          = models.DateTimeField(auto_now_add=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    creado_en      = models.DateTimeField(auto_now_add=True)
```

Cuatro campos que almacenan exactamente lo mismo. Imposible saber cuál es el "oficial" para reportes. Genera confusión en queries y en el admin de Django.

**Acción:** Migración para eliminar tres de ellos, conservar solo `creado_en`.

### 4.2 — `MovimientoCaja` tiene `fecha` y `creado_en` redundantes

```python
class MovimientoCaja(models.Model):
    fecha     = models.DateTimeField(auto_now_add=True)
    creado_en = models.DateTimeField(auto_now_add=True, null=True, blank=True)
```

Mismo problema. Eliminar `fecha`, conservar `creado_en`.

### 4.3 — `cargar_saldo` no registra movimiento de caja
**Archivo:** `views.py` → `cargar_saldo()`

```python
usuario.saldo += monto
usuario.save()
return redirect("panel_admin")
```

No queda ningún registro de quién cargó saldo, cuándo, ni por qué. Si hay una discrepancia contable, es imposible auditarla.

**Corrección:** Agregar `MovimientoCaja.objects.create(usuario=admin, tipo="ingreso", descripcion=f"Carga saldo para {usuario.correo}", monto=monto)`.

### 4.4 — `VerificacionInspector.infraccion_generada` nunca se marca `True`
El campo existe pero `crear_infraccion()` en `services_infracciones.py` nunca actualiza la verificación correspondiente. La trazabilidad inspector → infracción solo existe vía FK en `Infraccion`, no en `VerificacionInspector`.

### 4.5 — No hay log de acciones administrativas
Acciones como cambiar roles, crear inspectores o modificar tarifas no dejan rastro de quién las ejecutó ni cuándo. Para cumplimiento municipal esto es un problema mayor.

**Recomendación:** Usar `django-simple-history` o una tabla `AuditLog` manual para acciones críticas.

### 4.6 — `CierreCaja` tiene `creado_en` y `fecha_cierre` redundantes

```python
creado_en   = models.DateTimeField(default=timezone.now)
fecha_cierre = models.DateTimeField(auto_now_add=True)
```

Eliminar uno. Conservar `fecha_cierre` por semántica.

---

## 5. UX/UI — Conductores

### 5.1 — Warnings de vehículo nunca se muestran al conductor
En `estacionar_vehiculo`:
```python
result = ejecutar_estacionamiento(...)
warning = " | ".join(result.get("warnings", []))
...
return redirect(reverse(result["redirect"]))   # ← siempre redirige
```

El `warning` se arma pero nunca se pasa a ningún template porque siempre se hace redirect. Los avisos de "otro propietario registrado" o "usuario no verificado" se pierden silenciosamente.

**Corrección:** Usar `messages.warning(request, w)` antes del redirect para que el mensaje persista en la sesión.

### 5.2 — Flujo de finalización sin confirmación ni resumen de costo
`finalizar_estacionamiento` finaliza el estacionamiento y redirige al historial sin mostrar cuánto costó. El usuario no sabe cuánto se le descontó.

### 5.3 — `historial_estacionamientos` tiene dos URLs con distintos nombres

```python
path("historial/", views.historial_estacionamientos, name="historial_estacionamientos"),
path("mis_estacionamientos/", views.historial_estacionamientos, name="usuarios_historial_estacionamientos"),
```

Dos URLs para la misma vista. El decorador `finalizar_estacionamiento` redirige a `usuarios_historial_estacionamientos`. Otros links probablemente usen `historial_estacionamientos`. Consolidar en una sola.

### 5.4 — No hay página para agregar vehículo (template faltante)
`agregar_vehiculo` está en `urls.py` y en `views.py` pero no tiene template. El conductor no puede agregar vehículos desde la UI.

### 5.5 — Registro de usuarios asigna municipio por `Municipio.objects.first()`
```python
usuario.municipio = Municipio.objects.first()
```
Si hay múltiples municipios en el sistema, todos los registros nuevos van al municipio "primero" en la base de datos, sin lógica. En un sistema multi-municipio esto es un bug.

---

## 6. UX/UI — Inspectores

### 6.1 — `subcuadras_exentas=[...]` pasa lista literal `[Ellipsis]`
**Archivo:** `services_verificacion.py`

```python
return ResultadoVerificacion(
    ...
    subcuadras_exentas=[...],   # ← [Ellipsis], no lista vacía
)
```

El template que muestre `subcuadras_exentas` recibirá `[Ellipsis]` y mostrará `[...]`.

**Corrección:** `subcuadras_exentas=[]` o `subcuadras_exentas=None`.

### 6.2 — Resumen de cobros sin filtro ni paginación
`resumen_cobros` devuelve `MovimientoCaja.objects.all()` sin filtrar por municipio, inspector ni fecha, y no tiene paginación. En producción con miles de registros, la página va a ser lenta y mostrará datos de otros inspectores.

### 6.3 — Cierre de caja no muestra resumen antes de confirmar
El inspector puede cerrar la caja sin ver cuánto va a cerrar. No hay pantalla de confirmación.

### 6.4 — `panel_exenciones` no valida que la subcuadra sea del mismo municipio
El admin puede asignar exenciones en subcuadras de otros municipios si manipula el POST.

---

## 7. Gestión de usuarios, inspectores y vendedores

### 7.1 — Templates de gestión sin URLs configuradas
Las siguientes templates existen pero no tienen URLs ni views correspondientes:

| Template | Descripción |
|---|---|
| `admin/gestionar_usuarios.html` | Sin URL |
| `admin/gestionar_inspectores.html` | Sin URL |
| `admin/gestionar_vendedores.html` | Sin URL |
| `admin/gestionar_horarios.html` | Sin URL |
| `admin/gestionar_tarifas.html` | Sin URL |
| `admin/inicio_admin.html` | Sin URL |

Todo el CRUD de inspectores y vendedores depende del admin de Django (`/admin/`), que no es apto para usuarios operativos.

### 7.2 — No hay forma de deshabilitar usuarios desde el sistema
Solo desde el Django admin. No hay vista para activar/desactivar un inspector o conductor desde el panel administrativo del sistema.

### 7.3 — No hay gestión de tarifas desde el sistema
El modelo `Tarifa` existe pero no hay URL ni view para editarlo. Las views de cobro usan `TARIFA = Decimal("100")` hardcodeado, ignorando completamente el modelo.

### 7.4 — `Municipio` tiene campo `apellido`
```python
class Municipio(models.Model):
    nombre   = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)   # ← ¿?
```

Un municipio no tiene apellido. Parece un campo residual de un copy-paste de `Usuario`. Eliminarlo evita confusión.

### 7.5 — No hay gestión de horarios de estacionamiento
El sistema no tiene concepto de "horario habilitado". Se puede estacionar y generar infracciones a cualquier hora, incluso los días que el estacionamiento pago no está activo.

### 7.6 — `cargar_saldo` solo suma, nunca resta
No hay forma de corregir una carga incorrecta. Falta un view de ajuste o al menos de reversión de carga de saldo con auditoría.

---

## 8. Arquitectura (ADR)

### Estado actual

El sistema implementa una arquitectura de capas sana:
```
views → use_cases → services → domain
```

Los use cases tienen transacciones atómicas (`transaction.atomic`), las policies de dominio están separadas (`SaldoPolicy`, `VehiculoPolicy`), y los services son testeables sin Django.

### Decisiones pendientes y recomendaciones

#### ADR-001: Separación de `saldo` y `saldo_operativo`

**Contexto:** `Usuario` tiene dos campos de saldo. `saldo` es el del conductor (se descuenta al estacionar). `saldo_operativo` es el del inspector (se acumula al cobrar). No está documentado.

**Recomendación:** Documentar explícitamente y agregar comentarios en el modelo. Considerar si el inspector debería tener un modelo separado o si alcanza con roles.

#### ADR-002: VALIDACION_ACTIVA sin implementación

```python
VALIDACION_ACTIVA = False   # settings.py
```

Este flag existe en settings pero ningún view ni service lo lee. La validación está hardcodeada. Implementarlo o eliminarlo.

#### ADR-003: `registrar_estacionamiento_manual` vs flujo normal

El inspector manual usa `cobrar_estacionamiento` (solo crea `MovimientoCaja`) mientras que el vendedor usa `ejecutar_estacionamiento` (crea `Estacionamiento` + `MovimientoCaja`). Son dos flujos completamente distintos para la misma acción conceptual. Unificarlos.

#### ADR-004: Multi-municipio incompleto

El sistema tiene lógica multi-municipio en queries (`subcuadra__municipio=municipio`) pero en varios puntos usa `get_subcuadra_default()` que devuelve una sola subcuadra. Si el municipio tiene múltiples zonas, la subcuadra por defecto es arbitraria. Revisar si el inspector debe seleccionar la subcuadra al verificar.

#### ADR-005: SQLite en producción

`settings.py` usa SQLite. Para producción con múltiples inspectores operando simultáneamente, SQLite tiene limitaciones de concurrencia (escrituras secuenciales). Migrar a PostgreSQL antes del lanzamiento real.

#### ADR-006: Sin API REST

El sistema es server-side rendering puro. Si en el futuro se quiere una app móvil para inspectores (más natural en campo), habría que agregar DRF. Documentar esta decisión ahora para no diseñar templates que dificulten la migración.

---

## 9. Documentación

### Estado actual

Hay un archivo `docs/arquitectura.md` con descripción de capas. Es un buen punto de partida pero está incompleto y desactualizado respecto al código real.

### Qué falta documentar

**Models — decisiones de diseño:**
- Por qué `saldo` y `saldo_operativo` son campos distintos
- Qué significa que un vehículo sea `exento_parcial` vs `exento_global`
- El flujo de vida de un `Estacionamiento` (ACTIVO → FINALIZADO)
- El flujo de vida de una `Infraccion` (pendiente → pagada / anulada)

**Flujos de negocio:**
- Flujo completo del conductor: registro → cargar saldo → estacionar → finalizar
- Flujo del inspector: verificar → detectar impago → registrar infracción → cierre de caja
- Flujo del vendedor: cobrar en punto de venta → registrar estacionamiento
- Flujo del admin: crear inspector → asignar municipio → configurar tarifas

**Configuración de entorno:**
- Variables de entorno requeridas (`SECRET_KEY`, `DATABASE_URL`, `ENV`)
- Cómo correr migraciones en producción
- Cómo crear el superusuario inicial

**README actual:** Existe pero no describe cómo instalar ni correr el sistema localmente.

### Recomendación de estructura documental

```
docs/
  arquitectura.md         ← ampliar (existe)
  flujos_de_negocio.md    ← crear
  modelos.md              ← crear (decisiones de diseño)
  configuracion.md        ← crear (variables de entorno, deploy)
  api_reference.md        ← crear cuando se implemente la API
```

---

## 10. Estrategia de testing

### Estado actual

Hay un archivo `tests.py` con ~180 líneas que cubre:
- Estacionar (con y sin saldo)
- Verificación (todos los estados: NO_REGISTRADO, EXENTO, PAGADO, IMPAGO, PENDIENTE_PAGO)
- Crear infracción (OK y exento total)
- Login redirect por rol
- Cierre de caja básico
- Redirect de root por rol (todos los roles)

**Cobertura estimada: ~35% de los flujos críticos.**

### Qué falta testear

**Prioridad alta (bloquean producción):**

```python
# Acceso no autorizado a rutas protegidas
def test_inspector_no_puede_acceder_a_panel_admin(self):
def test_conductor_no_puede_acceder_a_panel_inspectores(self):
def test_anonimo_redirige_a_login(self):

# Pagar infracción
def test_pagar_infraccion_descuenta_saldo(self):
def test_pagar_infraccion_sin_saldo_falla(self):
def test_pagar_infraccion_ya_pagada_falla(self):

# Estacionamiento duplicado
def test_vehiculo_no_puede_tener_dos_estacionamientos_activos(self):

# Cierre de caja
def test_cierre_caja_bloquea_movimientos(self):
def test_cierre_caja_sin_movimientos_retorna_none(self):
```

**Prioridad media:**

```python
# Exenciones
def test_exento_total_no_puede_recibir_infraccion(self):
def test_exento_parcial_recibe_infraccion_en_otra_subcuadra(self):

# Carga de saldo
def test_cargar_saldo_aumenta_saldo_usuario(self):
def test_cargar_saldo_registra_movimiento(self):

# Flujo completo conductor
def test_flujo_completo_conductor(self):   # registro → estacionar → finalizar

# Registrar infracción reciente
def test_no_permite_segunda_infraccion_en_15_min(self):

# Multi-municipio
def test_inspector_no_ve_infracciones_de_otro_municipio(self):
```

**Prioridad baja:**

```python
# Roles múltiples (conductor que también es admin)
def test_usuario_con_multiples_roles(self):

# Vehículos con múltiples propietarios
def test_vehiculo_solo_puede_tener_un_propietario(self):

# Tolerancia
def test_tolerancia_15_min_entre_verificaciones_distintas(self):
```

### Recomendaciones de estructura

Separar `tests.py` en múltiples archivos:

```
tests/
  __init__.py
  test_estacionamiento.py
  test_infracciones.py
  test_verificacion.py
  test_caja.py
  test_auth_roles.py
  test_admin.py
  conftest.py           ← fixtures compartidos (municipio, usuario, subcuadra)
```

Agregar `pytest-cov` para medir cobertura:

```bash
pytest --cov=app_estacionamiento --cov-report=html
```

Meta realista para producción: **>70% de cobertura en flujos de negocio críticos**.

---

## 11. Roadmap de correcciones priorizadas

### Sprint 1 — Bloqueantes inmediatos (1–2 días)

1. Mover `Estacionamiento.Meta` dentro de la clase + migración
2. Corregir `from django.contrib import messages` en views.py
3. Agregar `@require_role` a `cerrar_caja` y `@require_role` a `simular_pago`
4. Conectar `pagar_infraccion` view con el use case correcto
5. Corregir `NameError` en `panel_exenciones`
6. Agregar `@require_login` o eliminar `simular_pago` si es solo para desarrollo

### Sprint 2 — Trazabilidad contable (2–3 días)

7. Migración para eliminar campos de fecha duplicados en `Infraccion` y `MovimientoCaja`
8. Agregar `MovimientoCaja` en `cargar_saldo`
9. Filtrar `resumen_cobros` por municipio del usuario autenticado
10. Marcar `VerificacionInspector.infraccion_generada = True` en `crear_infraccion`

### Sprint 3 — Gestión desde el sistema (1 semana)

11. Implementar views + URLs para gestionar inspectores, vendedores y tarifas
12. Conectar tarifa real desde modelo `Tarifa` en lugar de `Decimal("100")`
13. Implementar `registrar_estacionamiento_manual` para que cree un `Estacionamiento`
14. Agregar template `agregar_vehiculo.html`

### Sprint 4 — Calidad y testing (1 semana)

15. Separar `tests.py` en módulos por dominio
16. Agregar tests de permisos por rol
17. Agregar tests de flujo completo conductor
18. Configurar `pytest-cov` y alcanzar >70% de cobertura
19. Completar `docs/flujos_de_negocio.md` y `docs/configuracion.md`

### Antes de producción — Infraestructura

20. Migrar de SQLite a PostgreSQL
21. Separar settings dev/prod con variables de entorno
22. Remover `SECRET_KEY` hardcodeado
23. Habilitar `AUTH_PASSWORD_VALIDATORS`

---

*Auditoría generada el 2026-06-06. Revisión recomendada en cada sprint.*
