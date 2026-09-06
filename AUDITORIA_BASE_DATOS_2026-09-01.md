# Auditoría de base de datos — Estacionamiento Proyecto
Fecha: 2026-09-01
Stack: Django 5.x / PostgreSQL.

---

## Resumen ejecutivo

El modelo de datos es sólido para su escala. Los campos de dinero usan `DecimalField`, las fechas son timezone-aware, y las desnormalizaciones intencionales (snapshots en `CierreCaja`, `municipio` en `Infraccion`) están comentadas y justificadas. El hallazgo más relevante son tres relaciones con `on_delete=CASCADE` en modelos de auditoría (`VerificacionInspector` y `Infraccion`) que deberían ser `SET_NULL` o `PROTECT` para no borrar historial si alguien elimina un inspector, una subcuadra, o un vehículo. En la práctica es difícil que pase, pero es un riesgo latente.

---

## Lo que está bien ✅

- **Dinero**: todos los campos de monto usan `DecimalField` — no hay `FloatField` ni `IntegerField` para valores monetarios.
- **Fechas**: `DateTimeField` en todos los campos de fecha; `USE_TZ=True` en Django. Sin fechas como strings.
- **Patente como campo único**: `Vehiculo.patente = unique=True` → índice automático, no hay `filter(patente=...)` sin índice.
- **Snapshots en cierre de caja**: `CierreCaja.total_cobrado`, `ganancia_usuario`, `monto_municipio`, `porcentaje_ganancia_aplicado` son campos calculados al momento del cierre y no vuelven a cambiar. Patrón correcto para registros contables — comentado en el modelo.
- **Infracción.municipio con auto-fill**: el `save()` de `Infraccion` completa `municipio` desde `inspector.municipio` si está vacío. Desnormalización intencional para queries sin JOIN con inspector, documentada.
- **Constraint de único estacionamiento activo por vehículo**: `UniqueConstraint(fields=["vehiculo"], condition=Q(estado="ACTIVO"))` — garantiza a nivel DB que un vehículo no puede tener dos estacionamientos activos simultáneos. ✅
- **`mp_payment_id` único**: `MovimientoCaja.mp_payment_id = unique=True` — garantiza idempotencia de pagos de MercadoPago a nivel DB. ✅
- **Índices explícitos donde importa**: `VerificacionInspector(vehiculo, fecha)` y `PagoPublico(patente, estado)` + `(mp_payment_id)`.
- **`PROTECT` en relaciones contables críticas**: `Infraccion.vehiculo → PROTECT`, `Infraccion.inspector → PROTECT`, `MovimientoCaja.usuario → PROTECT`, `CierreCaja.usuario → PROTECT` — no se puede borrar un inspector o vehículo si tiene historial contable.

---

## Hallazgos

### 🟡 Media prioridad

#### 1. `Infraccion.subcuadra → CASCADE` — borrar subcuadra borra infracciones

**Qué es:**
```python
# models.py
subcuadra = models.ForeignKey(Subcuadra, on_delete=models.CASCADE, null=True, blank=True)
```

**Por qué es un problema:** si el admin elimina una subcuadra (ej. la calle se reorganiza), las infracciones registradas en esa subcuadra desaparecen de la base. Eso es historial contable borrado silenciosamente.

**Por qué no se nota hoy:** subcuadras rara vez se eliminan (se pueden desactivar o modificar). Pero si alguien limpia subcuadras de prueba en producción, el daño podría ser importante.

**Fix:**
```python
subcuadra = models.ForeignKey(Subcuadra, on_delete=models.SET_NULL, null=True, blank=True)
```
`SET_NULL` deja la infracción con `subcuadra=None` en vez de borrarla. Requiere una migración (solo cambia `on_delete`, sin cambio en schema — no necesita `makemigrations` si ya es `null=True`; sí necesita que la FK sea nullable, lo cual ya lo es).

Nota: `on_delete` en Django no se refleja en el schema de PostgreSQL (es a nivel ORM), así que la migración existe pero no requiere operaciones pesadas en la base.

---

#### 2. `VerificacionInspector` — `CASCADE` en las tres FK borra historial de auditoría

**Qué es:**
```python
inspector = models.ForeignKey(Usuario, on_delete=models.CASCADE)
vehiculo  = models.ForeignKey(Vehiculo, on_delete=models.CASCADE)
subcuadra = models.ForeignKey(Subcuadra, on_delete=models.CASCADE)
```

**Por qué es un problema:** `VerificacionInspector` es el registro de auditoría del trabajo del inspector — cuántos vehículos verificó, cuándo, en qué subcuadra. Si se borra un inspector (ej. renuncia y el admin elimina su cuenta), todas sus verificaciones históricas desaparecen. Lo mismo al borrar un vehículo o subcuadra.

**Por qué importa:** las verificaciones son la evidencia de trabajo del inspector (sirven para liquidar comisiones, detectar zonas sin cobertura, resolver disputas). Borrarlas por error sería un problema operativo.

**Fix propuesto:**
```python
inspector = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True)
vehiculo  = models.ForeignKey(Vehiculo, on_delete=models.SET_NULL, null=True, blank=True)
subcuadra = models.ForeignKey(Subcuadra, on_delete=models.SET_NULL, null=True, blank=True)
```

Requiere migración (agregar `null=True, blank=True` a las FK que actualmente no lo tienen). En el template que muestra el historial, agregar guards como `{{ verificacion.inspector.correo|default:"(inspector eliminado)" }}`.

Si la preferencia es que esos objetos nunca se puedan borrar mientras tengan verificaciones, `PROTECT` es igualmente válido y más explícito.

---

#### 3. `sia_titular` — formato inconsistente entre `Infraccion` y `Vehiculo`

**Qué es:**
- `Vehiculo.sia_titular_nombre` + `Vehiculo.sia_titular_apellido` — campos separados (correcto para filtrar/buscar por nombre o apellido individualmente)
- `Infraccion.sia_titular` — un solo `CharField(max_length=200)` con nombre completo concatenado

Misma entidad (titular del SIA), dos formatos distintos en dos modelos.

**Por qué importa:** si en el futuro se quiere buscar infracciones por apellido del titular SIA, habría que hacer `icontains` sobre el campo completo en vez de un filtro limpio. No es un bloqueo hoy porque la infracción y el vehículo son contextos distintos (la infracción guarda el titular *al momento de la fiscalización*), pero la inconsistencia de formato complica comparaciones futuras.

**Fix:** separar `Infraccion.sia_titular` en `sia_titular_nombre` + `sia_titular_apellido`, migrando los datos existentes (ej. `sia_titular.split(" ", 1)` como backfill inicial). Costo: migración + actualizar `views_inspector.py` donde se asigna `sia_titular`.

**Alternativa de menor costo:** agregar un comentario en el modelo explicando por qué está concatenado (ej. "La respuesta de ANDIS devuelve el nombre completo como string; los campos separados se pueden agregar en el futuro si se necesita filtrar por nombre/apellido"). Aceptable si la funcionalidad de búsqueda por nombre de titular no está en el roadmap cercano.

---

### 🟢 Baja prioridad

#### 4. `Estacionamiento.vehiculo → CASCADE` — borrar vehículo borra historial de estacionamientos

Similar al punto 2. En la práctica, los vehículos con infracciones no se pueden borrar (`PROTECT`), pero los que solo tienen estacionamientos (sin infracciones) sí. `SET_NULL` preservaría el historial. Bajo riesgo porque el admin raramente elimina vehículos.

---

#### 5. `Vehiculo.municipio → CASCADE` — inconsistencia con el modelo de conservar historia

Si se eliminara un municipio, sus vehículos desaparecerían. En la práctica esto está bloqueado por `Usuario.municipio → PROTECT` (no se puede borrar un municipio con usuarios), pero la inconsistencia conceptual existe. Bajo riesgo práctico.

---

#### 6. `horario_atencion` como texto libre en `Usuario`

```python
horario_atencion = models.CharField(max_length=200, blank=True, default="",
    help_text="Ej: Lun-Vie 9-18, Sáb 9-13")
```

Campo de texto libre para datos estructurados. Funciona para mostrar al usuario, pero no para filtrar vendedores por horario o calcular disponibilidad programáticamente. Si ese caso de uso aparece, reemplazarlo con un JSONField o una tabla `HorarioVendedor` aparte. Por ahora es aceptable — no hay lógica que consuma este campo.

---

#### 7. `Vehiculo.fecha_creacion` vs `creado_en` en el resto del sistema

La mayoría de los modelos usa `creado_en` como nombre del campo de fecha de creación. `Vehiculo` usa `fecha_creacion`. Inconsistencia menor, sin impacto funcional. Unificar en una refactorización futura si hay oportunidad (requeriría una migración de rename).

---

## Plan de acción incremental

En orden de prioridad:

1. **Cambiar `Infraccion.subcuadra → SET_NULL`** — es la más relevante porque las infracciones son el historial contable central. Sin migración de datos (la FK ya es `null=True`); solo un `makemigrations` que ajusta el `on_delete` (sin operación costosa en PostgreSQL).

2. **Cambiar `VerificacionInspector.*` a `SET_NULL` o `PROTECT`** — requiere migración que agrega `null=True` a las tres FK. Hay que actualizar los templates que accedan a estos campos con guards `|default`.

3. **`sia_titular` en `Infraccion`** — deferir para cuando se necesite filtrar por nombre de titular. Agregar comentario en el modelo mientras tanto.

4. **`Estacionamiento.vehiculo → SET_NULL`** — puede ir junto con el punto 2 si se hace una migración de modelos de auditoría.

5. **`horario_atencion` y `Vehiculo.fecha_creacion`** — deferir para un ciclo de refactorización posterior, no son urgentes.

---

## Notas

- No se ejecutó `EXPLAIN ANALYZE` contra la base real (sin acceso a producción). Los índices y constraints se auditaron por código fuente.
- La tabla `Usuario` mezcla campos de múltiples roles (inspector, vendedor, conductor) en un solo modelo. Es una decisión de diseño conocida y documentada (facilita el código Django vs. implementar herencia de modelos). No es un hallazgo — se documenta para que sea consciente, no accidental.
