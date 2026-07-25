# Auditoría de base de datos — Sistema de Estacionamiento Medido
Fecha: 2026-07-24

---

## Resumen ejecutivo

El modelo de datos es sólido en lo funcional: tipos correctos (DecimalField para dinero, DateTimeField con TZ), constraints bien pensados (UniqueConstraint parcial para estacionamiento activo, unique_together en abonos y horarios), y buena separación de responsabilidades entre modelos. Sin embargo hay **dos problemas estructurales serios** que pueden causar pérdida de datos o romper el multi-tenancy:

1. **`on_delete=CASCADE` en modelos contables** — borrar un inspector, un usuario o un municipio desde el Django Admin destruye infracciones, movimientos de caja y cierres, sin advertencia.
2. **`Subcuadra.unique_together` no incluye `municipio`** — dos municipios no pueden tener la misma calle+altura en el mismo sistema. Bug actual que bloquea escalar a más de un municipio con calles de nombre compartido.

Además hay tres campos muertos que solo agregan ruido: `Municipio.apellido`, `Infraccion.qr_code` y una duplicación temporal en `CierreCaja`.

---

## Hallazgos

### 🔴 Alta prioridad

#### 1. `on_delete=CASCADE` en modelos que guardan historial contable

**Afecta:** `Infraccion.inspector`, `Infraccion.vehiculo`, `MovimientoCaja.usuario`, `CierreCaja.usuario`, `Usuario.municipio`

**El problema:** Si desde el Django Admin se borra un inspector, un conductor o un municipio, el CASCADE silenciosamente elimina:
- Todas las infracciones labradas por ese inspector
- Todos los movimientos de caja de ese usuario
- Todos los cierres de caja

No hay advertencia. En un panel de Django Admin sin restricciones, esto es una bomba en producción.

**Impacto:** Pérdida irreversible de historial contable. Imposible de recuperar sin backup.

**Solución:** Cambiar a `PROTECT` en los modelos históricos. Si el código de negocio nunca necesita borrar inspectores o vehículos con historial (y no debería), `PROTECT` los defiende con un error claro en vez de borrar silenciosamente.

```python
# Infraccion
inspector  = models.ForeignKey(Usuario,   on_delete=models.PROTECT)
vehiculo   = models.ForeignKey(Vehiculo,  on_delete=models.PROTECT)
municipio  = models.ForeignKey(Municipio, on_delete=models.SET_NULL, null=True, blank=True)

# MovimientoCaja
usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT)

# CierreCaja
usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT)

# Usuario
municipio = models.ForeignKey(Municipio, on_delete=models.PROTECT, null=True, blank=True)
```

**Costo:** Una migración por modelo, reversible, sin backfill de datos.

---

#### 2. `Subcuadra.unique_together` no incluye `municipio`

**Código actual:**
```python
class Meta:
    unique_together = ("calle", "altura")
```

**El problema:** Si dos municipios distintos tienen la misma calle (ej: "San Martín 100"), el segundo falla al querer agregar la subcuadra. En un sistema multi-tenant donde `municipio` es el tenant, esto es un bug estructural.

**Impacto:** Bloquea agregar el segundo municipio si comparte nombre de calle con el primero. Ya ocurre si hay dos municipios usando "Zona Única".

**Solución:**
```python
class Meta:
    unique_together = ("municipio", "calle", "altura")
```

**Costo:** Una migración. Antes de aplicarla, verificar que no haya filas duplicadas en `(municipio, calle, altura)` — en testing no debería haber, pero conviene corroborar.

```python
# Verificación previa (correr en Django shell antes de migrar):
from app_estacionamiento.models import Subcuadra
from django.db.models import Count
Subcuadra.objects.values('municipio', 'calle', 'altura').annotate(n=Count('id')).filter(n__gt=1)
# → debe devolver QuerySet vacío
```

---

### 🟡 Media prioridad

#### 3. `Municipio.apellido` — campo muerto sin uso

```python
# models.py línea 162
apellido = models.CharField(max_length=100, blank=True)
```

No aparece en ningún template, vista, service ni test. Quedó de la migración 0003 (`0003_municipio_apellido_usuario_saldo_operativo_and_more`). Un municipio no tiene apellido.

**Solución:** `migrations.RemoveField(model_name='municipio', name='apellido')`. Sin backfill necesario. Verificar que ninguna consulta lo referencie antes.

---

#### 4. `Infraccion.qr_code` — campo muerto sin uso

```python
# models.py línea 462
qr_code = models.CharField(max_length=255, null=True, blank=True)
```

Agregado en migración 0008 (`0008_infraccion_monto_infraccion_qr_code`). No se usa en ningún lugar del código. Además usa `null=True` en `CharField` (Django recomienda solo `blank=True` en CharField, no `null=True`, para evitar dos representaciones del "vacío": `NULL` y `""`).

**Solución:** Remover el campo. Es `null=True` así que no hay datos perdidos (ninguna fila debería tener un valor real).

---

#### 5. `CierreCaja.creado_en` vs `fecha_cierre` — mismo dato dos veces

```python
fecha_cierre = models.DateTimeField(auto_now_add=True)   # auto al crear
creado_en    = models.DateTimeField(default=timezone.now) # también al crear
```

Ambos se setean al mismo momento. `creado_en` con `default=timezone.now` en vez de `auto_now_add=True` permite en teoría pasarle un valor manual, pero en la práctica siempre coincide con `fecha_cierre`. La diferencia es sutil pero genera confusión.

**Solución:** Evaluar si `creado_en` se usa en algún lugar además de auditoría. Si no, removerlo. Si sí, documentar por qué existe junto a `fecha_cierre`.

---

#### 6. `MovimientoCaja.tipo` sin `choices` en el modelo

```python
tipo = models.CharField(max_length=10)  # egreso / ingreso
```

Los valores `"ingreso"` y `"egreso"` se usan hardcodeados en el código pero no están definidos como `choices` en el modelo. Esto significa que en principio cualquier string puede entrar en el campo (sin validación a nivel DB o modelo).

**Solución:**
```python
TIPOS = [("ingreso", "Ingreso"), ("egreso", "Egreso")]
tipo = models.CharField(max_length=10, choices=TIPOS)
```

No requiere migración de datos, solo actualizar el campo (Django no aplica `choices` a nivel SQL, es solo validación de formulario y documentación).

---

#### 7. `VerificacionInspector.resultado` sin `choices`

```python
resultado = models.CharField(max_length=50)
```

Valores como `"LIBRE"`, `"INFRACCIONAR"`, `"EXENTO_TOTAL"`, etc. entran como texto libre. No hay validación en el modelo. Si en algún momento se escribe mal (ej: `"LIBRE "` con espacio), un filtro como `.filter(resultado="LIBRE")` falla silenciosamente.

**Solución:** Agregar `choices` con los valores definidos en `services/verificacion.py`.

---

#### 8. `saldo_operativo` puede desincronizarse de `MovimientoCaja`

`saldo_operativo` es un running total que `services/caja.py` suma con `select_for_update()`. Correcto en condiciones normales. Pero si algún movimiento de caja se crea por fuera de ese service (directo en tests, en el admin Django, o por un bug), el `saldo_operativo` queda desactualizado respecto a la suma real de `MovimientoCaja`.

No hay ningún mecanismo de reconciliación ni check periódico.

**Impacto:** Bajo por ahora (el flujo está controlado), pero se convierte en un problema si el historial de un usuario se modifica manualmente.

**Solución práctica:** Agregar una función `recalcular_saldo_operativo(usuario)` que haga `sum(MovimientoCaja.monto where not cerrado)` y permita corregir desincronías en caso de necesidad. No es urgente, pero tenerla disponible evita futuros dolores de cabeza.

---

### 🟢 Baja prioridad

#### 9. `Vehiculo.fecha_creacion` inconsistente con convención del sistema

```python
fecha_creacion = models.DateTimeField(auto_now_add=True, null=True)
```

El resto del sistema usa `creado_en` (Infraccion, AbonoMensual, MovimientoCaja, etc.). Naming inconsistente.

**Solución:** Migración con `RenameField`. Sin impacto en datos, hay que actualizar los lugares del código que lo usen (probablemente ninguno, porque `fecha_creacion` de Vehiculo no se referencia en ninguna vista visible).

---

#### 10. `Infraccion.municipio` es desnormalización no documentada

La infracción guarda `municipio` directamente, aunque ya está en `inspector.municipio` y `subcuadra.municipio`. El `save()` lo auto-popula. Está bien como optimización de queries, pero no está documentado como decisión intencional.

```python
# Falta un comentario como:
# municipio — desnormalización intencional para filtrar infracciones
# sin hacer JOIN con inspector. Siempre debe coincidir con inspector.municipio.
```

---

#### 11. `SolicitudVerificacion.nombre/apellido/dni` duplican campos de `Usuario`

Al crear la solicitud, el conductor ingresa nombre, apellido y DNI que en principio coinciden con `Usuario.first_name`, `Usuario.last_name`. Es un snapshot del momento de la solicitud (útil para auditoría), pero no está documentado como tal. Alguien leyendo el código podría pensar que son la única fuente de verdad de esos datos.

---

## Plan de acción incremental

Aplicar en este orden (cada paso es independiente del siguiente):

**Paso 1 — Subcuadra.unique_together** (5 min, riesgo bajo)
1. Correr el query de verificación de duplicados en Django shell
2. Crear migración: `AlterUniqueTogether` de `("calle", "altura")` a `("municipio", "calle", "altura")`
3. Aplicar

**Paso 2 — Cambiar on_delete en modelos contables** (15 min, riesgo bajo)
- Una sola migración que cambia `CASCADE → PROTECT` en: `Infraccion.inspector`, `Infraccion.vehiculo`, `MovimientoCaja.usuario`, `CierreCaja.usuario`, `Usuario.municipio`
- `Infraccion.municipio`: cambiar a `SET_NULL` (ya tiene `null=True`)
- Correr los 89 tests después para confirmar que nada se rompe

**Paso 3 — Remover campos muertos** (10 min, riesgo bajo)
- Una migración que remueve `Municipio.apellido` e `Infraccion.qr_code`
- Verificar antes que no haya referencias en templates ni código (ya verificado arriba: ninguna)

**Paso 4 — Agregar choices** (5 min, sin migración de datos)
- `MovimientoCaja.tipo` y `VerificacionInspector.resultado`: agregar `choices` al campo
- No requiere migración de datos (Django no aplica choices en SQL)

**Paso 5 — Renombrar `fecha_creacion` → `creado_en` en Vehiculo** (opcional, diferible)
- Migración `RenameField`. Solo si hay tiempo y no hay templates que lo usen.

---

## Notas

- No se revisaron las migraciones intermedias en detalle (41 en total). El historial parece lineal y sin fusiones raras. La evolución es razonable.
- `saldo_operativo` está activo en el flujo de caja — no es un campo muerto. El riesgo es de desincronización, no de inutilidad.
- Los totales precalculados en `CierreCaja` y `Rendicion` son snapshots intencionales y correctos — no son redundancia problemática.
- Los campos de múltiples roles en `Usuario` (campos de inspector + campos de vendedor en la misma tabla) son una decisión pragmática válida para este tamaño de sistema. No se propone separar en tablas por rol — el costo de esa refactorización no justifica el beneficio.
