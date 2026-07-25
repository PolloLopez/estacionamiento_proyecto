# Auditoría de rendimiento — Sistema de Estacionamiento
Fecha: 2026-07-24  
Stack: Django 5.2 / PostgreSQL (Railway) / sin frameworks JS  
Síntoma reportado: auditoría preventiva (no hay queja puntual hoy)  
Volumen actual: ~1 municipio en testing, pocos conductores.  
Volumen esperado: municipio real con 100–500 conductores activos y años de historial.

> **Nota de contexto:** Ninguno de estos problemas es perceptible hoy con datos de prueba.
> El riesgo real es al pasar a producción municipal con más datos. Ese es el momento
> en que una lista sin paginar con 800 registros empieza a tardar varios segundos.

---

## Resumen ejecutivo

Tres cuellos de botella concretos, todos en vistas que van a usarse a diario en producción:

1. **`historial_estacionamientos`** trae todos los estacionamientos del conductor sin límite —
   con 2 años de uso diario son 700+ registros de un golpe, sin `select_related`.
2. **`gestionar_usuarios`** trae todos los conductores del municipio sin paginar —
   con 400 conductores son 400 objetos + sus vehículos en memoria a la vez.
3. **`cerrar_estacionamientos_vencidos_por_horario`** se llama en cada visita al home del conductor,
   y cuando el horario termina hace un loop con una escritura por estacionamiento activo (N+1).

Los tres tienen fix directo con `Paginator` y una pequeña refactorización. Ningun cambio
de infraestructura ni caché sofisticado necesario para el volumen esperado.

---

## Hallazgos

### 🔴 Alta prioridad

---

**1. `historial_estacionamientos` sin paginación ni `select_related`**

- **Dónde:** `views_conductor.py` → `historial_estacionamientos` (línea 603-613)
- **Qué pasa:**
  ```python
  estacionamientos = (
      Estacionamiento.objects
      .filter(usuario=usuario)
      .order_by("-hora_inicio")
      # ← sin límite, sin select_related, sin only()
  )
  ```
  Con 1 estacionamiento por día durante 2 años → 730 objetos traídos de un golpe.
  El template accede a `est.vehiculo.patente` y `est.subcuadra` sin que la vista haya
  hecho `select_related`, lo que dispara 1 query extra por registro (`vehiculo` y `subcuadra`
  por separado). Con 50 registros son ~100 queries adicionales.
- **Cuándo empeora:** escala con el historial del conductor. No se nota en testing.
- **Fix:** `Paginator` (20 por página) + `select_related("vehiculo", "subcuadra")`.

---

**2. `gestionar_usuarios` sin paginación**

- **Dónde:** `views_admin.py` → `gestionar_usuarios` (línea 596-614)
- **Qué pasa:**
  ```python
  usuarios = Usuario.objects.filter(
      es_conductor=True, municipio=municipio
  ).prefetch_related("vehiculos")
  ```
  Trae TODOS los conductores del municipio con todos sus vehículos en memoria.
  `prefetch_related("vehiculos")` está bien — evita N+1 — pero sin paginación
  con 400 conductores son 400 objetos + sus N vehículos en una sola query.
  La vista ya tiene búsqueda por `q` (filtro en DB), pero sin paginación cuando
  no se filtra se trae todo.
- **Cuándo empeora:** escala con el número de conductores registrados en el municipio.
- **Fix:** `Paginator` (50 por página). Mantener el `prefetch_related`.

---

**3. `cerrar_estacionamientos_vencidos_por_horario` en cada request del conductor**

- **Dónde:** `views_conductor.py` → `inicio_usuarios` (línea 88-89), llama a
  `services/horarios.py` → `cerrar_estacionamientos_vencidos_por_horario`
- **Qué pasa:**
  ```python
  # En inicio_usuarios — se ejecuta CADA vez que el conductor abre su home:
  if usuario.municipio:
      cerrar_estacionamientos_vencidos_por_horario(usuario.municipio)
  ```
  Y dentro de esa función:
  ```python
  if horario and hora_actual > horario.hora_fin:
      activos = Estacionamiento.objects.filter(estado="ACTIVO", subcuadra__municipio=municipio)
      for est in activos:          # ← loop con 1 finalización por iteración
          finalizar_estacionamiento_uc(est)
  ```
  Dos problemas:
  - **Siempre:** hace 1 query a `HorarioEstacionamiento` en cada visita al home,
    aunque no sea la hora de cierre (fuera de la ventana de cierre, que es casi siempre).
    Esta query no tiene caché (a diferencia de `puede_estacionar_ahora` que sí cachea).
  - **Al cierre del día:** si 10 conductores abren el home simultáneamente en la ventana
    de cierre, los 10 intentan cerrar los mismos estacionamientos a la vez — trabajo
    duplicado y riesgo de race condition (aunque el `select_for_update` en `finalizar_estacionamiento_uc`
    probablemente lo protege).
- **Fix:** agregar un flag en caché para marcar que el cierre ya se hizo hoy, igual al
  patrón que usa `puede_estacionar_ahora`. El cierre solo corre una vez por municipio
  por noche.

---

### 🟡 Media prioridad

---

**4. `VerificacionInspector` sin índice en `(vehiculo, fecha)` y crece indefinidamente**

- **Dónde:** `services/verificacion.py` línea 65-67, y el modelo en `models.py`.
- **Qué pasa:**
  ```python
  verificacion_anterior = VerificacionInspector.objects.filter(
      vehiculo=vehiculo
  ).order_by("-fecha").first()
  ```
  PostgreSQL tiene índice automático en `vehiculo_id` (FK), pero para el `ORDER BY -fecha`
  tiene que ordenar todos los registros del vehículo en memoria antes de devolver el primero.
  Con 3 inspectores × 100 verificaciones/día × 250 días = ~75.000 registros/año.
  Con 2 años: 150.000 registros. La query se vuelve perceptiblemente lenta.
- **Fix:** índice compuesto `(vehiculo_id, fecha DESC)` en una migración. O limitar el
  historial de verificaciones con un campo de fecha en el filtro (ej. `filter(vehiculo=v,
  fecha__gte=hace_30_dias).order_by("-fecha").first()`).

---

**5. `admin_infracciones` con slice `[:200]` hardcodeado sin paginación real**

- **Dónde:** `views_admin.py` → `admin_infracciones` (línea 762):
  ```python
  "infracciones": infracciones[:200],
  ```
- **Qué pasa:** se traen hasta 200 infracciones con `select_related` (correcto, sin N+1),
  pero no hay paginación. El admin no puede ver las infracciones más antiguas que la #200.
  No es un problema de velocidad hoy — la query con `select_related` y límite de 200 es
  rápida. Es un problema funcional que se va a notar cuando haya más de 200 en el período
  filtrado.
- **Fix:** reemplazar el slice por `Paginator`.

---

### 🟢 Baja prioridad

---

**6. `MovimientoCaja.save()` hace una query extra en cada actualización**

- **Dónde:** `models.py` → `MovimientoCaja.save()` (línea 388-393):
  ```python
  def save(self, *args, **kwargs):
      if self.pk:
          original = MovimientoCaja.objects.get(pk=self.pk)  # ← query extra
          if original.cerrado:
              raise Exception(...)
      super().save(*args, **kwargs)
  ```
  Cada vez que se actualiza un `MovimientoCaja` existente, hace un `SELECT` adicional
  para leer el estado `cerrado`. La query es por PK (O(log n), rápida), pero podría
  optimizarse trayendo solo el campo necesario.
- **Fix menor:** `MovimientoCaja.objects.filter(pk=self.pk).values_list("cerrado", flat=True).first()`
  — trae solo el booleano. Impacto perceptible solo con cierres de caja en batch grandes.

---

## Qué está bien (no tocar)

- **`puede_estacionar_ahora`** — usa `cache.set(timeout=3600)` correctamente, no hace
  queries en cada request del horario. Referencia ideal para el fix del punto 3.
- **`admin_infracciones`** — tiene `select_related("vehiculo", "inspector", "subcuadra")`,
  sin N+1. Solo le falta paginación real.
- **`gestionar_usuarios`** — tiene `prefetch_related("vehiculos")`, sin N+1. Solo le falta paginación.
- **`panel_admin`** — `conductores.count` en el template dispara un `SELECT COUNT(*)`,
  no trae todos los objetos a memoria. Correcto.
- **`inicio_usuarios`** — el estacionamiento activo se busca con `.first()` (límite 1).
  Las notificaciones se filtran por `leida=False`. Los abonos con `.select_related("vehiculo")`.
  Ningún N+1 detectado.
- **`verificar_estado_vehiculo`** — las queries de `Estacionamiento`, `AbonoMensual` y
  `VerificacionInspector` usan `.first()` o `.exists()`, sin traer listas completas.

---

## Plan de acción incremental

| # | Dónde | Fix | Esfuerzo | Riesgo |
|---|-------|-----|----------|--------|
| 1 | `historial_estacionamientos` | Paginator (20/pág) + `select_related` | 20 min | Ninguno |
| 2 | `gestionar_usuarios` | Paginator (50/pág) | 15 min | Ninguno |
| 3 | `cerrar_estacionamientos_vencidos_por_horario` | Cache "ya cerrado hoy" | 30 min | Bajo |
| 4 | `VerificacionInspector` | Índice `(vehiculo_id, fecha DESC)` en migración | 15 min | Bajo (migración ligera en tabla sin muchos datos hoy) |
| 5 | `admin_infracciones` | Paginator real (reemplazar `[:200]`) | 30 min | Bajo |
| 6 | `MovimientoCaja.save()` | `values_list("cerrado")` en vez de `get()` | 10 min | Ninguno |

Aplicar 1, 2 y 4 antes de cualquier demo o apertura a más municipios. El 3 (caché de cierre)
es una mejora de robustez — no urgente mientras haya un municipio solo.
