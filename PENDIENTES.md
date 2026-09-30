# Pendientes — Estacionamiento Medido Municipal

Última actualización: 2026-09-30 (sesión 27 — UX subcuadra compacta, preselección de vehículo, API JSON fase 2)

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

**Estrategia actual:** Django como shell (navbar, routing, base), React como capa interactiva embebida. Sin DRF — `JsonResponse` puro hasta que la escala lo justifique.

**Fases:**
- **Fase 2** ✅ (esta sesión): API JSON pura — `views_api.py` con `GET /api/conductor/dashboard/` y `GET /api/conductor/estacionamientos/activos/`. Sin DRF, sin dependencias nuevas.
- **Fase 3** (próxima): Componente `PanelEstado` en React — timer de cuenta regresiva + botón "Renovar", montado en `inicio_usuarios.html`. Primer componente React real en producción.
- **Fase 4**: Flujo completo del conductor en React (estacionar, historial, perfil).
- **Fase 5**: `verificar.html` del inspector en React (verificación + GPS + infracciones).

**Pendiente antes de Fase 3:** validar en producción que `GET /api/conductor/dashboard/` y `/api/conductor/estacionamientos/activos/` devuelven los datos correctos con un conductor real logueado. Chequear en Network tab del navegador.

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
