# Pendientes — Estacionamiento Medido Municipal

Última actualización: 2026-09-29 (sesión 26 cont. — fixes UX/bugs post-testing: timer vencido, confirm dialog, decimal_places)

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

### Migración frontend a React (SPA con DRF + JWT)

**Decisiones tomadas:** Vite + React SPA · JWT (djangorestframework-simplejwt) · Railway (backend) + Vercel (frontend) · migración incremental por rol.

**Estimación:** ~14-20 sesiones. Las primeras 3-4 son más lentas por curva de aprendizaje.

**Fases:**
- **Fase 0** (1 sesión): DRF + JWT en backend. `pip install djangorestframework djangorestframework-simplejwt django-cors-headers`. Crear `api/` app, endpoint `/api/v1/auth/login/` y `/api/v1/auth/refresh/`.
- **Fase 1** (3-4 sesiones): Conductor. Setup Vite en `frontend/`, AuthContext + Axios interceptor de refresh, 6 páginas (Login, Inicio, Estacionar, Historial, Perfil, Verificacion). Deploy Vercel apuntando a Railway.
- **Fase 2** (2-3 sesiones): Inspector. Verificar vehículo, infraccionar, GPS subcuadra.
- **Fase 3** (5-7 sesiones): Admin. El más complejo — subcuadras, staff, reportes, rendiciones, verificaciones.
- **Fase 4** (1-2 sesiones): Vendedor + Tesorero.
- **Fase 5** (2-3 sesiones): Superadmin. Puede quedar en Django templates por más tiempo sin impacto real.

**Valor clave:** los componentes repetidos hoy (`<SelectorSubcuadra />`, modal SIA, tarjetas de vehículo, banner zona libre) pasan a ser un componente único reutilizable en todos los roles.

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
