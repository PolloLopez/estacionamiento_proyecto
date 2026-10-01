# Pendientes — Estacionamiento Medido Municipal

Última actualización: 2026-10-01 (sesión 30 — Fase 4C React: FormularioEstacionar implementado)

---

## 🗺️ Estado del deploy

| Ambiente | Estado |
|---|---|
| **Railway** (`develop` → `main`) | ✅ Activo — ambiente de prueba / demo municipal |
| **Digital Ocean App Platform** | ⏳ Opcional — solo si el contrato exige SLA formal |

### Orden recomendado antes del go-live real

```
1. Test e2e comisiones (🟡 abajo)
2. Fix bug /pagar/ fuera de horario (🟡 abajo)
3. Subir Railway a plan Pro (backups)
4. Smoke test completo por rol
5. Switch de dominio al municipio real
```

---

## 🔴 Alta prioridad

### Fase 4C — FormularioEstacionar ✅ (sesión 30 — pendiente smoke test en producción)

`estacionar_vehiculo.html` migrado a React con fallback Django siempre activo.

**Qué se implementó:**
- `GET /api/conductor/datos-estacionar/` — datos frescos para el form (vehículos, opciones, subcuadras, saldo, horario)
- `POST /api/conductor/estacionar/` — llama a `ejecutar_estacionamiento` use case, devuelve JSON, setea `notif_infraccion_pendiente` en sesión
- `formulario_estacionar_conductor.js` — componente React con GPS, cascade subcuadra, tarjetas vehículo, botones duración, submit a API
- `estacionar_vehiculo.html` actualizado: mount point React + fallback Django en `#formulario-estacionar-fallback`

**Checklist smoke test en producción (próxima sesión):**
- [ ] Flujo completo: seleccionar vehículo → GPS detecta subcuadra → elegir duración → confirmar → panel inicio actualizado
- [ ] Caso abono activo: badge y bloqueo de confirmación
- [ ] Caso fuera de horario: formulario bloqueado (opacidad)
- [ ] Caso zona libre: no muestra sección duración, acepta confirm con $0
- [ ] Eliminar vehículo desde la tarjeta React
- [ ] Fallback Django sigue funcionando si se desactiva JS
- [ ] 202+ tests OK

---

### Subir Railway a plan Pro ($20/mes) — backups automáticos

Railway Hobby **no hace backups del PostgreSQL**. Si la base se corrompe, no hay recuperación. Para un sistema municipal con datos de ciudadanos esto es inaceptable.

**Un solo paso:** Railway dashboard → proyecto → plan → "Upgrade to Pro" → $20/mes flat, backups activados.

**Backup manual inmediato** (antes de cualquier deploy importante):
```powershell
# Con Railway CLI:
railway run pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql
# Con DBeaver (GUI gratuita): clic derecho en DB → Backup
```

---

---

## 🟡 Media prioridad

### Bug — `/pagar/` sin login: "ESTACIONAR AHORA" visible fuera de horario

`pago_publico/detalle_patente.html` muestra el botón "ESTACIONAR AHORA" aunque el municipio esté fuera de horario. Verificar si la vista `detalle_patente` chequea `puede_estacionar_ahora()` antes de renderizar el botón, y ocultarlo fuera de horario con mensaje explicativo (mismo patrón que `estacionar_vehiculo.html`).

---

### Saldo negativo para conductores (habilitado por superadmin, límite por admin municipal)

Permitir que un conductor estacione aunque su saldo llegue a cero, hasta un límite negativo configurable.

**Modelo:** agregar en `Municipio`:
- `saldo_negativo_habilitado = BooleanField(default=False)` — superadmin habilita por municipio
- `limite_saldo_negativo = DecimalField(max_digits=10, decimal_places=2, default=0)` — cuántos pesos puede quedar en negativo (ej: $500)

**Impacto:**
- `debitar_saldo_conductor()`: si `saldo_negativo_habilitado`, permitir llegar hasta `-limite_saldo_negativo`
- `saldo_insuficiente` en la API: considerar el límite negativo disponible
- UI conductor: aviso visual cuando está usando saldo negativo
- UI admin: campo editable en `editar_municipio.html`
- UI superadmin: checkbox en panel de municipio

---

### Superadmin: controlar declaración de domicilio electrónico en conductores

Dos configuraciones nuevas en `Municipio`:
1. `domicilio_electronico_conductor_activo = BooleanField(default=True)` — si False, el checkbox no aparece en `/solicitar-verificacion/` ni en el perfil del conductor
2. `domicilio_electronico_leyenda = TextField(default="Email declarado para notificaciones oficiales...")` — texto personalizable por municipio

Requiere migración + UI en `editar_municipio.html` + respetar el flag en `solicitar_verificacion.html` e `inicio_usuarios.html`.

---

### Bug — liquidación: "Monto variable (% recaudación)" calcula mal

En `/superadmin/municipio/1/liquidacion/nueva/`, el porcentaje variable debe calcularse sobre el total recaudado en el período. Revisar si está calculando sobre otro valor (monto base, suma de rendiciones, etc.).

---

### Comisiones de vendedores — test end-to-end

Prueba manual completa según `GUIA_TESTING_ROLES.md` → sección "TEST COMPLETO: Flujo de comisiones de vendedores". Hacer antes del go-live.

---

### Selector de subcuadra en `/pagar/` público (`detalle_patente.html`)

La pantalla de pago público todavía usa `<select>` encadenados (cascada vieja). Actualizar al mismo patrón `<datalist>` + matching por altura/intersección que ya tienen `estacionar_vehiculo.html`, `verificar.html` y `registrar_infraccion.html`.

---

## 🟢 Baja prioridad / Futuras versiones

### Superadmin: configurar tamaño de fuente en ticket de infracción y QR

El ticket de infracción (`ticket_infraccion.html`) y el QR de pago tienen un tamaño de fuente fijo. Diferentes impresoras térmicas y diferentes tamaños de papel pueden requerir ajustes de fuente. Propuesta:

1. Agregar `Municipio.ticket_fuente_size = IntegerField(default=14)` y `qr_fuente_size = IntegerField(default=12)` (o un campo único de escala: `ticket_escala_pct = IntegerField(default=100)`).
2. Exponer el campo en `editar_municipio.html` → sección de impresión.
3. Pasar el valor al template del ticket e inyectarlo como variable CSS o inline style en el contenedor principal.

**Por qué vale la pena evaluarlo**: cada municipio puede tener impresoras distintas (58mm vs 80mm) y el texto puede quedar cortado o demasiado grande. Un campo configurable evita hardcodear y tener que deployar para ajustar la impresión.

**Evaluación pendiente**: revisar si conviene un slider (1–3: pequeño/normal/grande) o un campo numérico libre. Un slider tipo `<input type="range" min="10" max="20">` es más amigable para un admin no técnico.

---

### Migración frontend a React — hibridación incremental (sin DRF por ahora)

**Estrategia:** Django como shell (navbar, routing, base), React como capa interactiva embebida. Sin DRF — `JsonResponse` puro. Sin Vite — UMD + `React.createElement` (sin JSX, sin build step).

**React se sirve desde static propio** (`static/app_estacionamiento/js/react.production.min.js` y `react-dom.production.min.js`) — no desde CDN externo.

**Fases:**
- **Fase 2** ✅: API JSON — `views_api.py` con `GET /api/conductor/dashboard/` y `GET /api/conductor/estacionamientos/activos/`.
- **Fase 3** ✅: `PanelEstado` en `inicio_usuarios.html` — timer de cuenta regresiva, polling 30s, estados múltiples. En producción.
- **Fase 4A** ✅: `HistorialConductor` en `/mis_estacionamientos/` — paginación sin recarga, expand/collapse. Modal inline de renovar en `PanelEstado` — timer se actualiza sin recargar. `calcular_opciones_duracion` respeta `duracion_minima_min` en franja final.
- **Fase 4B** ✅: `MisVehiculos` en `/inicio/` — badges 🟢/🔵/⚪, infracciones pendientes, links a historial. Fallback Django siempre presente.
- **Fase 4C** ✅ (sesión 30): FormularioEstacionar — `estacionar_vehiculo.html`. Pendiente smoke test en prod. Ver sección 🔴 arriba.
- **Fase 5**: Inspector en React — pantalla de verificación + GPS + infracciones.

---

### Registro anticipado de estacionamiento

Si el conductor registra antes de que inicie el horario (ej: 07:58, apertura 08:00), permitir el registro pero fijar `hora_inicio` en la hora de apertura del municipio. Actualmente se bloquea hasta las 08:00.

---

### Staff con doble rol

Admin, tesorero e inspectores deberían poder gestionar su saldo y estacionamientos como conductores.

---

### Migración a Digital Ocean App Platform *(solo si contrato municipal exige SLA formal)*

DO App Platform Basic ($12) + DO PostgreSQL dev ($15) = $27/mes + trabajo de migración vs. Railway Pro $20/mes plano. Migrar solo si el municipio exige contractualmente SLA 99.99% o certificaciones ISO 27001. Si se migra: hacerlo en paralelo sin apagar Railway; actualizar webhook MercadoPago, variables de entorno, DNS y cron jobs.

---

### Otras mejoras futuras

- **OCR de patentes con cámara** — actualmente hay botón básico. Mejora real con Google ML Kit o Tesseract.js para el inspector en campo. Evaluar post go-live.
- **Tutorial GIFs en landing pública** — el tutorial por rol ya existe en `<details>`. Versión con GIFs animados para la landing pública.
- **Pago diario (módulo premium)** — superadmin habilita por municipio, municipio asigna valor. Requiere diseño de modelo.
- **2FA (verificación de dos pasos)** — para admin y tesorero. `django-otp` o `django-two-factor-auth`. Evaluar después de la migración a DO.
- **Inspector cancela infracción** — admin autoriza por municipio: inspector puede anular una infracción otorgando un período de gracia.
- **`/admin/mapa-infracciones/` — ChunkLoadError en consola** — error de la extensión Chrome Excalidraw, NO del código. La página funciona. Verificar desactivando la extensión.

---

> El historial completo de cambios por sesión está en `CONTEXT.md` → sección "Historial de cambios por sesión".
