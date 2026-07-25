# Auditoría de base de datos — Sistema de Estacionamiento
Fecha: 2026-07-25
Stack: Django 5.2 / PostgreSQL (Railway)
Base auditada: `models.py` (43 migraciones aplicadas, historial lineal y sin parches raros).

> **Nota de contexto:** El sistema está en testing con un municipio y pocos conductores.
> Los hallazgos 🔴 no están rompiendo cosas hoy, pero son correctables con pocas
> líneas de código antes de que entren datos reales en producción.

---

## Resumen ejecutivo

El modelo está bien estructurado en general: usa `DecimalField` para montos, `auto_now_add`
correcto, `choices` consistentes, `on_delete` pensado (PROTECT donde corresponde). Hay un bug
silencioso real en `duracion_horas` que puede hacer que estacionamientos de media hora se
registren con la duración equivocada. Los otros 🔴 son problemas de integridad referencial que
ya se corrigieron en `Infraccion` pero se olvidaron en `VerificacionInspector` y `VehiculoUsuario`.

---

## Hallazgos

### 🔴 Alta prioridad

---

**1. `Estacionamiento.duracion_horas` es `IntegerField` pero el sistema maneja medias horas**

- **Dónde:** `models.py` línea 348, `factories.py` línea 18, `estacionar_vehiculo.py` línea 127
- **Qué pasa:**
  ```python
  # models.py
  duracion_horas = models.IntegerField(default=1)

  # factories.py — recibe duracion=Decimal("1.5")
  Estacionamiento.objects.create(duracion_horas=duracion, ...)
  # Django hace int(Decimal("1.5")) = 1 → truncamiento silencioso
  ```
  `calcular_opciones_duracion()` genera opciones en múltiplos de 0.5h (1h, 1.5h, 2h...).
  Cuando el conductor elige "1h 30min", `duracion=Decimal("1.5")` llega a la factory.
  Django convierte silenciosamente: `int(Decimal("1.5"))` = `1`.
  - El **costo** se cobra bien: `costo_base = 1.5 × tarifa` (DecimalField, calculado antes).
  - Pero `hora_inicio + timedelta(hours=1)` vence 30 minutos antes de lo pagado.
  - El inspector vería el vehículo como infractor cuando el conductor tiene 30 min pagados aún.
- **Impacto si no se corrige:** infracciones injustas para conductores que eligen duraciones
  de media hora. Difícil de detectar porque el costo siempre es correcto, solo la expiración
  está mal.
- **Fix:** cambiar a `DecimalField(max_digits=4, decimal_places=1)` + migración de datos.
  Los datos existentes son todos enteros (siempre truncaron a entero) — la migración es segura.
  También ajustar el cálculo en `views_conductor.py:665` que hace `int(horas_extra)` al renovar.

---

**2. `VerificacionInspector` — CASCADE en inspector y vehiculo (historial de auditoría en riesgo)**

- **Dónde:** `models.py` líneas 454-456
  ```python
  inspector = models.ForeignKey(Usuario, on_delete=models.CASCADE)   # ← debería ser PROTECT
  vehiculo  = models.ForeignKey(Vehiculo, on_delete=models.CASCADE)   # ← ídem
  subcuadra = models.ForeignKey(Subcuadra, on_delete=models.CASCADE)
  ```
- **Qué pasa:** Si un inspector se desvincula del municipio y el admin borra su usuario,
  se pierden todas sus verificaciones históricas. Lo mismo si se borra un vehículo.
  `Infraccion` ya corrigió esto con `on_delete=models.PROTECT` en inspector y vehiculo
  (migración 0042), pero `VerificacionInspector` quedó con CASCADE.
- **Impacto:** pérdida de auditoría de cuántos vehículos verificó cada inspector, lo que
  afecta el cálculo de productividad y el historial de qué vehículos fueron chequeados.
- **Fix:** `on_delete=models.PROTECT` en inspector y vehiculo. `subcuadra` puede quedarse
  en CASCADE (es metadata de lugar, no una relación contable crítica).
  Migración solo de `AlterField` — sin backfill necesario.

---

**3. `VehiculoUsuario` sin `unique_together` — el par (usuario, vehiculo) puede duplicarse**

- **Dónde:** `models.py` líneas 249-263
  ```python
  class VehiculoUsuario(models.Model):
      usuario  = models.ForeignKey(Usuario, on_delete=models.CASCADE)
      vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE)
      # ← sin unique_together ni UniqueConstraint
  ```
- **Qué pasa:** El M2M de Django con `through` manual **no agrega** la unicidad automática
  que sí agrega el M2M implícito. Cualquier código que haga
  `VehiculoUsuario.objects.create(usuario=u, vehiculo=v)` dos veces inserta dos filas.
  El método `save()` maneja la unicidad de `es_propietario`, pero no impide duplicados del par.
  Si hay dos filas `(usuario=u, vehiculo=v)`, `vehiculos = models.ManyToManyField` en
  `Usuario` podría devolver el mismo vehículo dos veces en querys sin `.distinct()`.
- **Impacto:** potencial duplicación de vehículos en listas del conductor. No rompe nada
  hoy, pero es una constraint de negocio real que debería estar en la DB.
- **Fix:**
  ```python
  class Meta:
      unique_together = ("usuario", "vehiculo")
  ```
  La migración fallará si hay filas duplicadas existentes — verificar con un `SELECT`
  antes de aplicarla en producción. En testing no debería haber duplicados.

---

**4. `Estacionamiento.hora_inicio` y `creado_en` son siempre idénticos**

- **Dónde:** `models.py` líneas 345 y 353
  ```python
  hora_inicio = models.DateTimeField(auto_now_add=True)
  # ...
  creado_en   = models.DateTimeField(auto_now_add=True)
  ```
- **Qué pasa:** Ambos usan `auto_now_add=True`, así que siempre tienen el mismo valor.
  `creado_en` no aporta información adicional. Confunde a quien lee el modelo
  ("¿hay alguna diferencia entre estos dos campos?") y ocupa espacio innecesario.
- **Impacto:** bajo en producción, pero es una señal de deuda técnica. El riesgo futuro es
  que alguien asuma que pueden diferir y filtre por uno en vez del otro.
- **Fix opciones:**
  - **A (recomendado):** eliminar `creado_en` — `hora_inicio` es más descriptivo y ya
    es el que usan todas las vistas. Migración de `RemoveField` simple.
  - **B:** convertir `hora_inicio` en campo editable (quitar `auto_now_add`) para poder
    registrar estacionamientos retroactivos si algún día se necesita. Más flexible,
    más riesgo de error en creación.

---

### 🟡 Media prioridad

---

**5. Inconsistencia de nombres para el timestamp de creación**

- **Qué pasa:** tres convenciones en el mismo proyecto:
  - `creado_en` — la mayoría de los modelos (correcto)
  - `fecha_creacion` — `Vehiculo` (único que usa este nombre)
  - `fecha` — `VerificacionInspector` (el nombre menos descriptivo)
- **Impacto:** hay que recordar el nombre correcto para cada modelo al filtrar.
  `Vehiculo.fecha_creacion` y `VerificacionInspector.fecha` no son detectados por una
  búsqueda de `creado_en` en el código.
- **Fix:** renombrar con `RenameField` en dos migraciones separadas:
  - `Vehiculo.fecha_creacion` → `creado_en`
  - `VerificacionInspector.fecha` → `creado_en`
  Riesgo bajo — solo requiere actualizar las pocas referencias en views y templates.

---

**6. `Infraccion.estado` y `Estacionamiento.estado` sin índices compuestos**

- **Qué pasa:** las queries más frecuentes del sistema filtran por estado junto con
  otra FK, pero no hay índice compuesto:
  ```python
  # En inicio_usuarios y al estacionar — varias veces por sesión:
  Infraccion.objects.filter(municipio=municipio, estado="pendiente")

  # En inicio_usuarios — en cada home del conductor:
  Estacionamiento.objects.filter(usuario=usuario, estado="ACTIVO").first()

  # En cerrar_estacionamientos:
  Estacionamiento.objects.filter(estado="ACTIVO", subcuadra__municipio=municipio)
  ```
  El índice automático de FK cubre el primer campo, pero el filtro adicional por `estado`
  implica un scan parcial. Con miles de infracciones o estacionamientos, esto se nota.
- **Fix:** dos índices compuestos en una sola migración:
  ```python
  # En Infraccion.Meta:
  models.Index(fields=["municipio", "estado"], name="idx_infraccion_municipio_estado")

  # En Estacionamiento.Meta:
  models.Index(fields=["usuario", "estado"], name="idx_estacionamiento_usuario_estado")
  ```

---

**7. `Notificacion` — `(destinatario_id, leida)` sin índice compuesto**

- **Qué pasa:** en cada visita al home del conductor:
  ```python
  notificaciones = Notificacion.objects.filter(destinatario=usuario, leida=False)
  ```
  El FK da índice en `destinatario_id`, pero el filtro adicional `leida=False` hace un
  scan de todas las notificaciones del usuario. Con el tiempo (meses de notificaciones
  acumuladas), un conductor con historial largo sufre un scan creciente en cada home.
- **Fix:**
  ```python
  # En Notificacion.Meta:
  models.Index(fields=["destinatario", "leida"], name="idx_notificacion_dest_leida")
  ```

---

**8. `CierreCaja.periodo` y `SolicitudVerificacion.estado_exencion` con `blank=True, default=""`**

- **Qué pasa:**
  ```python
  periodo = models.CharField(max_length=10, choices=PERIODOS, blank=True, default='')
  estado_exencion = models.CharField(max_length=20, choices=ESTADOS, blank=True, default="")
  ```
  El valor `""` (string vacío) no está en `PERIODOS` ni en `ESTADOS`. Django valida
  `choices` solo en formularios, no en la DB. Esto significa que el Django Admin
  puede mostrar el valor vacío sin label, o la vista puede hacer
  `get_periodo_display()` y obtener `""` en vez de un label legible.
- **Fix:** agregar `("", "-")` como primera opción en cada `choices`, o cambiar el default
  a `None` y poner `null=True` si el campo es realmente opcional.

---

### 🟢 Baja prioridad

---

**9. `Vehiculo.fecha_creacion` con `null=True` y `auto_now_add=True` (combinación redundante)**

- `auto_now_add=True` siempre asigna el valor al crear, nunca puede ser null.
  El `null=True` probablemente se agregó cuando se añadió el campo en una migración
  para no romper filas existentes (patrón válido), pero ya se puede quitar.
- Sin urgencia — no afecta queries ni datos.

---

**10. `SolicitudVerificacion.dni` vs `Usuario.numero_dni` — naming inconsistente**

- El mismo dato (DNI) se llama `dni` en `SolicitudVerificacion` y `numero_dni` en
  `Usuario`. No causa bugs, pero obliga a recordar dos nombres diferentes.
- Si en algún momento se cruza el dato entre ambos modelos en código, es fácil confundirse.

---

**11. `Usuario` mezcla campos de todos los roles en una sola tabla**

- Campos de inspectores (`telefono`, `numero_dni`, `numero_legajo`) y vendedores
  (`nombre_propietario`, `documento_cuil`, `horario_atencion`) conviven en el mismo modelo.
  Para el volumen actual (decenas de usuarios), no es un problema.
- Si el sistema escala a cientos de municipios con decenas de vendedores cada uno,
  una tabla `PerfilVendedor` / `PerfilInspector` separada daría más claridad.
- Por ahora: 🟢, mantener como está, solo documentar que es una desnormalización
  consciente por practicidad del modelo Django + Auth.

---

## Plan de acción incremental

| # | Dónde | Fix | Migración necesaria | Riesgo |
|---|-------|-----|---------------------|--------|
| 1 | `Estacionamiento.duracion_horas` | `IntegerField` → `DecimalField(max_digits=4, decimal_places=1)` | Sí — `AlterField` (datos existentes son enteros, compatibles) | Bajo |
| 2 | `VerificacionInspector` | `on_delete=CASCADE` → `PROTECT` en inspector y vehiculo | Sí — `AlterField` (no toca datos) | Ninguno |
| 3 | `VehiculoUsuario` | Agregar `unique_together = ("usuario", "vehiculo")` | Sí — verificar duplicados antes en producción | Bajo |
| 4 | `Estacionamiento.creado_en` | Eliminar campo redundante | Sí — `RemoveField` (no se usa en ninguna view) | Ninguno |
| 5 | `Infraccion` + `Estacionamiento` | Índices compuestos en estado | Sí — `AddIndex` (sin backfill, solo crea el índice) | Ninguno |
| 6 | `Notificacion` | Índice `(destinatario, leida)` | Sí — `AddIndex` | Ninguno |
| 7 | `Vehiculo.fecha_creacion` | Renombrar a `creado_en` | Sí — `RenameField` | Bajo (actualizar templates/views que lo usen) |
| 8 | `VerificacionInspector.fecha` | Renombrar a `creado_en` | Sí — `RenameField` | Ninguno (el campo no se usa en vistas) |
| 9 | `CierreCaja.periodo` / `SolicitudVerificacion.estado_exencion` | Agregar `("", "-")` a choices | No — solo cambio de choices en Python | Ninguno |

**Orden recomendado:** 1 → 2 → 3 → 5+6 (en una migración) → 4 → 7+8 (en otra migración) → 9.
Empezar por el 1 porque tiene impacto en datos reales (el inspector puede multar erróneamente).
Los #5 y #6 se pueden agrupar en una sola migración de índices.

---

## Qué está bien (no tocar)

- **`DecimalField` para todos los montos** — sin riesgo de redondeo. Consistente en todo el modelo.
- **`USE_TZ=True` y timezone-aware** — ningún campo guarda fechas como string.
- **Snapshots en `CierreCaja` y `Rendicion`** — `total_cobrado`, `ganancia_usuario`,
  `porcentaje_ganancia_aplicado`, `total_neto` son desnormalizaciones intencionales y bien
  documentadas. Correcto para datos contables que no deben cambiar al actualizar la tarifa.
- **`UniqueConstraint` en `Estacionamiento`** — solo un ACTIVO por vehículo, a nivel DB.
  Esto es la constraint más importante del negocio y está bien implementada.
- **`unique_together` en `Subcuadra`** — `(municipio, calle, altura)` correctamente multi-tenant.
- **`on_delete=PROTECT` en modelos contables** — `MovimientoCaja`, `CierreCaja`, `Rendicion`,
  `Infraccion`. La corrección de la migración 0042 cubre los casos más críticos.
- **`AbonoMensual.unique_together = ("vehiculo", "municipio", "mes")`** — evita doble abono.
- **Índice compuesto en `VerificacionInspector`** — ya agregado en migración 0043.

---

## Notas

- No se revisaron los datos reales de la DB de Railway (sin acceso directo). Si hay datos
  en producción, verificar con `SELECT COUNT(*), vehiculo_id, usuario_id FROM app_estacionamiento_vehiculousuario GROUP BY vehiculo_id, usuario_id HAVING COUNT(*) > 1`
  antes de aplicar el `unique_together` del punto 3.
- El hallazgo 1 (`duracion_horas`) puede verificarse con
  `SELECT id, duracion_horas, costo_base FROM app_estacionamiento_estacionamiento WHERE duracion_horas != ROUND(costo_base / <tarifa_hora>)`.
  Si hay filas donde los valores no coinciden, confirma que el truncamiento ocurrió.
