# Auditoría de rendimiento — Estacionamiento Proyecto
Fecha: 2026-09-01
Síntoma reportado: auditoría preventiva (no hay lentitud reportada). Foco en detectar lo que puede romperse cuando el sistema pase de demo a producción real con datos de un municipio.

---

## Resumen ejecutivo

El sistema está bien armado para su escala actual. Paginación presente en todas las listas largas, `select_related`/`prefetch_related` donde corresponde, queries con `annotate`/`aggregate` en vez de loops Python. El único hallazgo relevante es el dashboard de estadísticas del admin, que agrega **todos los datos históricos sin filtro de fecha** — hoy con pocos datos de prueba no se nota, pero con 2 años de uso real de un municipio será la primera vista que se haga lenta. Los demás hallazgos son preventivos, de bajo riesgo para la demo actual.

---

## Lo que está bien ✅

- **Paginación**: `gestionar_usuarios` (50/pág), `admin_infracciones` (50/pág), `historial_estacionamientos` (20/pág). Las listas históricas no traen todo de una sola vez.
- **`select_related`/`prefetch_related`**: `panel_admin` usa `select_related("vehiculo","inspector")` en infracciones recientes; `gestionar_usuarios` usa `prefetch_related("vehiculos")`; `admin_infracciones` usa `select_related("vehiculo","inspector","subcuadra")`. Sin N+1 visible en las vistas más usadas.
- **Conteos con `.count()`**: `verificaciones_pendientes` y `rendiciones_pendientes` en `panel_admin` usan `.count()` en vez de traer todos los objetos a memoria.
- **Dashboard de staff con `annotate`**: `auditoria_staff` computa cobros, comisiones, verificaciones e infracciones con `annotate(Sum, Count, Max)` — una sola query por tabla en vez de un loop por vendedor/inspector.
- **Cierre de estacionamientos vencidos por horario**: `cerrar_estacionamientos_vencidos_por_horario()` usa el cache de Django (`cache_key_cierre_{municipio_id}_{fecha}`) para no repetir el trabajo más de una vez por día por municipio, aunque se llame en cada visita al panel de conductores. Patrón correcto para un sistema sin Celery.
- **Índices ya existentes**: `VerificacionInspector` tiene índice compuesto `(vehiculo, fecha)` para la query más frecuente. `PagoPublico` tiene índices en `(patente, estado)` y `mp_payment_id`.

---

## Hallazgos

### 🟡 Media prioridad

#### 1. `dashboard_admin` agrega datos históricos sin filtro de fecha

**Qué es:** la vista `dashboard_admin` (renderizada desde `panel_admin`) corre 3 queries que agregan **todo el historial** del municipio sin restricción temporal:

```python
# infracciones por inspector: TODAS las infracciones, sin fecha
infracciones_por_inspector = Infraccion.objects.filter(municipio=municipio) \
    .values("inspector__correo").annotate(total=Count("id"))

# vehículos por día: TODOS los vehículos registrados
patentes_por_dia = Vehiculo.objects.filter(municipio=municipio) \
    .annotate(fecha=TruncDate("fecha_creacion")).values("fecha").annotate(total=Count("id"))

# cobros: TODOS los MovimientoCaja del municipio, sin fecha
cobros = MovimientoCaja.objects.filter(usuario__municipio=municipio) \
    .values("usuario__correo").annotate(total=Sum("monto"))
```

**Por qué va a doler:** con 2 años de uso real, `Infraccion` puede tener 50.000+ registros y `MovimientoCaja` varios miles. El `GROUP BY` sobre toda esa tabla es O(todas las filas). Hoy con datos de demo no se nota.

**Cuándo empeora:** crece con el tiempo. No con usuarios concurrentes, sino con la acumulación histórica.

**Fix propuesto:** acotar a un período razonable por defecto (ej. últimos 30 días) con la opción de cambiar el rango. Ya se tiene el patrón en `auditoria_staff` (filtro `desde/hasta`):

```python
# En dashboard_admin, limitar a los últimos 30 días por default
desde = timezone.now().date() - timedelta(days=30)

infracciones_por_inspector = Infraccion.objects.filter(
    municipio=municipio,
    creado_en__date__gte=desde,   # ← agregar filtro
).values("inspector__correo").annotate(total=Count("id")).order_by("-total")
```

Lo mismo para `cobros` y `patentes_por_dia`. Agregar controles de fecha al template si se quiere permitir al admin ver períodos específicos.

**Costo:** bajo. No requiere migración ni cambios en el modelo.

---

### 🟢 Baja prioridad

#### 2. `estacionamientos_activos` en `panel_admin` sin límite

**Qué es:** en `panel_admin`, los estacionamientos activos del municipio se traen sin ningún cap:

```python
estacionamientos_activos = Estacionamiento.objects.filter(
    subcuadra__municipio=municipio,
    estado="ACTIVO",
).select_related("vehiculo", "subcuadra").order_by("-hora_inicio")
# ← sin [:N]
```

**Por qué puede doler:** en hora pico de un municipio mediano (ej. 300 autos estacionados simultáneamente), trae 300 objetos cuando quizás el template solo muestra los 20 más recientes.

**Por qué no es urgente ahora:** los estacionamientos activos son por naturaleza acotados en número (la capacidad física de la zona). No crecen indefinidamente como el historial.

**Fix propuesto:** agregar un cap de seguridad:
```python
estacionamientos_activos = Estacionamiento.objects.filter(
    subcuadra__municipio=municipio, estado="ACTIVO"
).select_related("vehiculo", "subcuadra").order_by("-hora_inicio")[:50]
```

Y verificar cuántos muestra realmente el template de `panel_admin.html` para afinar ese número.

---

#### 3. Sin índices compuestos en `Infraccion` y `MovimientoCaja`

**Qué es:** los campos más usados en combinación en queries frecuentes no tienen índices compuestos explícitos. Django crea índice automático en FK (ej. `municipio_id`), pero no en combinaciones:

- `Infraccion(municipio, creado_en)` — usada en `admin_infracciones`, `dashboard_admin`
- `MovimientoCaja(usuario, tipo, creado_en)` — usada en `auditoria_staff`, `resumen_caja`

**Por qué no es urgente ahora:** con volumen de demo, el FK index de `municipio_id` ya filtra bien y el resultado es chico. Empieza a importar cuando hay 100.000+ filas en esas tablas.

**Fix propuesto (cuando escale a producción real):** en `models.py`:

```python
class Infraccion(models.Model):
    ...
    class Meta:
        indexes = [
            models.Index(fields=["municipio", "-creado_en"], name="idx_inf_municipio_fecha"),
        ]

class MovimientoCaja(models.Model):
    ...
    class Meta:
        indexes = [
            models.Index(fields=["usuario", "tipo", "-creado_en"], name="idx_mov_usuario_tipo_fecha"),
        ]
```

Requiere `makemigrations` + `migrate`. Aplicar antes del primer deploy con datos reales de municipio.

---

#### 4. `notificaciones_nuevas` sin cap en `inicio_usuarios`

**Qué es:** se traen todas las notificaciones no leídas del conductor:
```python
notificaciones_nuevas = Notificacion.objects.filter(
    destinatario=usuario, leida=False
).order_by("-fecha")
```

**Por qué no es urgente:** en la práctica serán 1-5. Solo podría ser un problema si alguien nunca marca ninguna como leída y acumula cientos (improbable).

**Fix mínimo:** `.order_by("-fecha")[:20]` como cap de seguridad.

---

## Plan de acción incremental

En orden de impacto/riesgo:

1. **Filtro de fechas en `dashboard_admin`** — antes del próximo go-live real. 5 líneas de código. Sin migración. Bajo riesgo. El único cambio visible para el admin es que las estadísticas sean del último mes en vez de "toda la historia".

2. **Cap de seguridad en `estacionamientos_activos`** — con la misma oportunidad. 1 línea. Sin impacto en funcionalidad.

3. **Índices compuestos en `Infraccion` y `MovimientoCaja`** — al momento de migrar a Digital Ocean (producción real). Requiere migración. En una tabla grande, `CREATE INDEX` puede tardar unos minutos — Railway no tiene downtime en `migrate`, pero si la tabla tiene muchas filas en Railway puede tardar. Hacerlo en una ventana de mantenimiento o verificar si Railway aguanta el tiempo de creación de índice en el deploy.

4. **Cap en `notificaciones_nuevas`** — cuando haya oportunidad. Mínimo impacto, mínimo riesgo.

---

## Notas

- No se tuvo acceso a producción ni a herramientas de profiling (django-debug-toolbar, logs de queries). El diagnóstico es por inspección de código — los números reales solo se pueden confirmar con datos de un municipio real.
- El sistema **no usa React** en el frontend — es Django templates puro. Los puntos del checklist sobre renders innecesarios y `useMemo` no aplican.
- El patrón de auto-cierre de estacionamientos via cache es suficiente para la demo. Para producción real con muchos conductores abriendo el home simultáneamente, considerar un cron job de Railway o una tarea periódica de Django-Q para hacer el cierre de forma proactiva en vez de reactiva.
