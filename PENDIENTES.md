# Pendientes — Estacionamiento Medido Municipal

Última actualización: 2026-09-25 (sesión 20 — bugs V1.0.1 + DB password Railway)

---

## 🗺️ Estado del deploy

| Ambiente | Estado |
|---|---|
| **Railway** (`develop` → `main`) | ✅ Activo — ambiente de prueba / demo municipal |
| **Digital Ocean App Platform** | 🔴 Pendiente — destino de producción real |

### Orden recomendado antes del go-live real

```
1. Test e2e comisiones completo (🟡 abajo)
2. Fix verificar.html SUBCUADRAS_INS (🟡 abajo)
3. Migrar a Digital Ocean App Platform (🔴 abajo)
4. Smoke test en DO con URL temporal
5. Switch de dominio al municipio real
```

---

## 🔴 Alta prioridad

### Subir Railway a plan Pro ($20/mes) — backups + deploy estable

**Conclusión luego de evaluar Railway vs Digital Ocean:**
Railway Pro a $20/mes plano (app + PostgreSQL con point-in-time recovery incluido) es mejor opción que DO App Platform + DO PostgreSQL ($27/mes + trabajo de migración). Mismas certificaciones operativas para la escala actual, cero fricción.

**Por qué es urgente:** Railway en el plan Hobby **no hace backups automáticos del PostgreSQL**. Si la base de datos se corrompe o se borra por error, no hay recuperación. Para un sistema municipal con datos de ciudadanos esto es inaceptable.

**Implementación (un solo paso):**
Railway dashboard → tu proyecto → plan → "Upgrade to Pro" → $20/mes flat, backups activados automáticamente.

**Backup manual inmediato (antes de subir de plan o ante cualquier deploy importante):**
```powershell
# Instalar herramientas PostgreSQL (solo una vez)
winget install PostgreSQL.PostgreSQL   # destildar todo excepto "Command Line Tools"

# Exportar la base de datos
pg_dump "postgresql://postgres:PASSWORD@acela.proxy.rlwy.net:27429/railway" > backup_2026-09-24.sql
```
O sin instalar nada: Railway CLI → `railway run pg_dump $DATABASE_URL > backup.sql`
O con GUI: DBeaver (gratuito) → clic derecho en DB → Backup.

**Regenerar contraseña Railway (si quedó expuesta):**
Railway dashboard → servicio Postgres → Settings → Danger Zone → "Reset Password".

---

### Notificaciones push al conductor

El conductor no recibe aviso cuando le queda poco tiempo ni cuando vence el abono. La app ya es PWA con `sw.js` registrado.

**Implementación:**
1. Generar VAPID keys (`py -m py_webpush generatekeys`).
2. Instalar `pywebpush` + modelo `SuscripcionPush(usuario, endpoint, p256dh, auth)`.
3. Endpoint `/push/suscribir/` que guarda la suscripción del navegador.
4. Extender `sw.js` para manejar el evento `push` y mostrar la notificación.
5. Tarea programada (o señal Django) X minutos antes del vencimiento — configurable por municipio.
6. Misma infra para abono: aviso N días antes del vencimiento mensual.

**Nota:** no mezclar con el modelo `Notificacion` (avisos in-app). Las push son notificaciones del SO.

---

### Migración a Digital Ocean App Platform *(solo si el contrato municipal exige SLA formal)*

**Conclusión:** DO App Platform Basic ($12) + DO PostgreSQL dev ($15) = **$27/mes + trabajo de migración**. Railway Pro a $20/mes plano incluye lo mismo para la escala actual. Migrar a DO solo si la municipalidad exige contractualmente el SLA 99.99% formal o las certificaciones ISO 27001.

Si se decide migrar: hacer en paralelo sin apagar Railway hasta confirmar que DO funciona. Actualizar webhook de MercadoPago, variables de entorno, DNS y cron jobs.

**Paso 1 — Preparar DO (sin tocar Railway)**
1. DO → App Platform → "Create App" → conectar repo GitHub (rama `main`).
2. Run command: `gunicorn estacionamiento.wsgi --bind 0.0.0.0:$PORT`
3. Build command: `pip install -r requirements.txt && python manage.py collectstatic --noinput`
4. Post-deploy job: `python manage.py migrate`
5. Agregar PostgreSQL (~$7/mes dev) → DO inyecta `DATABASE_URL` automáticamente.

**Paso 2 — Variables de entorno en DO** (copiar de Railway, salvo `DATABASE_URL` que DO inyecta sola):
`SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS` (URL temporal DO + dominio final), `CLOUDINARY_*`, `MP_ACCESS_TOKEN`, `MP_PUBLIC_KEY`, `MP_WEBHOOK_SECRET`, `ANYMAIL_*`, `SENTRY_DSN`.

**Paso 3 — Migrar base de datos**
```bash
pg_dump $RAILWAY_DATABASE_URL > backup_railway_$(date +%Y%m%d).sql
psql $DO_DATABASE_URL < backup_railway_YYYYMMDD.sql
python manage.py migrate --check
```
Si Railway solo tiene datos de prueba, saltar el dump y correr solo `migrate`.

**Paso 4 — Cron job en DO** (Jobs en schedule):
- Nombre: `revocar-exenciones` / Command: `python manage.py revocar_exenciones_vencidas` / Schedule: `0 3 * * *`

**Paso 5 — Smoke test (URL temporal, sin tocar DNS)**
- [ ] Login de cada rol
- [ ] Estacionamiento completo (débito de saldo)
- [ ] Infracción + cobro
- [ ] Rendición de vendedor → admin certifica → tesorero deposita
- [ ] Emails (Brevo/Resend)
- [ ] Cloudinary sirve imágenes

**Paso 6 — Switch de dominio**
1. DO → Settings → Domains → agregar dominio del municipio. SSL automático.
2. DNS del registrador → apuntar a DO. Propagación: 5–30 min.
3. ⚠️ **Actualizar webhook de MercadoPago** → fácil de olvidar.
4. Actualizar UptimeRobot con la nueva URL.
5. Dejar Railway activo 3–5 días como fallback, después apagar.

---

## 🟡 Media prioridad

### Bug — liquidación: "Monto variable (% recaudación)" calcula mal

En `/superadmin/municipio/1/liquidacion/nueva/`, el campo "Monto variable — % recaudación ($)" debe calcular el porcentaje sobre el **total recaudado por el municipio en el período seleccionado**. Revisar si está calculando sobre otro valor (ej. sobre el monto base, o sobre la suma de rendiciones, en lugar de la recaudación total del período).

---

### Comisiones de vendedores — test end-to-end

Hacer ANTES de la migración a DO. Prueba manual completa según `GUIA_TESTING_ROLES.md` → sección "TEST COMPLETO: Flujo de comisiones de vendedores".

---

### Fix `verificar.html` — SUBCUADRAS_INS + autocomplete sel-calle + teclado numérico sel-altura

Tres issues relacionados en el flujo del inspector:
- `SUBCUADRAS_INS` bug pendiente de diagnóstico
- Autocomplete en `sel-calle` (datalist)
- `inputmode="numeric"` en `sel-altura`

---

## 🟢 Baja prioridad / Futuras versiones

- **Staff con doble rol** — admin, tesorero e inspectores deberían poder gestionar su saldo y estacionamientos como conductores.
- **OCR de patentes con cámara** — actualmente hay botón básico. Mejora real con Google ML Kit o Tesseract.js para el inspector en campo. Evaluar post go-live.
- **Tutorial GIFs en landing pública** — el tutorial por rol ya existe en `<details>`. Versión con GIFs animados para la landing pública.
- **Pago diario (módulo premium)** — superadmin habilita por municipio, municipio asigna valor. Requiere diseño de modelo.
- **2FA (verificación de dos pasos)** — para admin y tesorero. `django-otp` o `django-two-factor-auth`. Evaluar después de la migración a DO.
- **Inspector cancela infracción** — admin autoriza por municipio: inspector cancela una infracción otorgando un período de gracia desde el momento de la infracción.
- **`/admin/mapa-infracciones/` — ChunkLoadError en consola** — son errores de la extensión Chrome Excalidraw (`chrome-extension://lkeokcighogdliiajgbbdjibidaaeang`), NO del código. La página funciona correctamente. Verificar desactivando la extensión.

---

## ✅ Resuelto — sesión 20 (2026-09-25)

- **BLE doble diálogo al infraccionar**: `reconectarImpresora()` abría un diálogo filtrado por nombre; si fallaba, `imprimirActa()` abría un segundo `acceptAllDevices`. Eliminado el diálogo filtrado de `reconectarImpresora()` → ahora retorna null y se abre un solo diálogo limpio.
- **`agregar_vehiculo.html` botón sin estilo**: `class="btn-general"` no existe en `global.css` → cambiado a `class="btn"`.
- **`renovar_estacionamiento.html` preview calcula mal con 30 min**: `LANGUAGE_CODE = "es-ar"` renderea `Decimal("0.5")` como `"0,5"` → `parseFloat` retorna 0. Agregado `{% load l10n %}` y `|unlocalize` en los 4 valores (3 en el bloque `<script>` + `data-horas` en el botón).
- **Railway DB password**: contraseña reseteada vía `ALTER USER postgres WITH PASSWORD '...'` + actualización de `DATABASE_URL` en app service.

---

## ✅ Resuelto — sesiones 18–19 (2026-09-24) — V1.0.1

**UX conductor — `estacionar_vehiculo.html`:**
- `sel-altura` muestra altura + referencia de cuadra: "500 — Entre Av. San Martín y Belgrano" (antes solo el texto entre calles, sin número de altura).
- Botones diferenciados visualmente: GPS → azul outline (`btn-detectar-cuadra`); duración seleccionada → nuevo `.duracion-activa` (azul sólido, toggle con clase dedicada en lugar de swapear `btn`/`btn-outline`); Confirmar → verde (#28a745). Tres acciones → tres colores distintos.
- "Otros vehículos vinculados" colapsado en `<details>` — el conductor casi siempre usa los recientes; los demás no ocupan pantalla por defecto.
- Tarjetas de vehículo: `font-size:1.1rem` + `letter-spacing:1.5px` + `word-break:break-all` + `min-width:130px` para que patentes de 7 chars (AA123BB) no desborden.
- `renovar_estacionamiento`: fracciones de 30 min disponibles al renovar (`duracion_minima_min=30` forzado en la vista), antes solo de a 1 hora.

**UX conductor — `inicio_usuarios.html`:**
- Línea de estado del estacionamiento dice "hasta HH:MM" (hora calculada desde el timer JS, `horaVencStr`) en lugar de "desde HH:MM".
- Botón 🔄 Renovar inline junto a la ubicación y hora de vencimiento.

**UX admin — `subcuadras.html`:**
- Popup Leaflet con botón ✏️ Editar subcuadra (atributos `data-*` + event delegation en `#mapa`).
- Filtro de búsqueda en la tabla de subcuadras.
- Click en primera celda de una fila → resalta la fila y centra el mapa en el marcador (`flyTo`).
- Instrucciones colapsadas en `<details>` (antes siempre visibles).
- Formulario unificado de nueva subcuadra: GPS opcional capturado desde click en el mapa; si no se clickea el mapa, crea la subcuadra marcada como "SIN GPS".
- Eliminado toggle numérico `id="toggle-numerico"` confuso.
- Pin 🏛️ de sede municipal en el mapa (requería que `views_admin.py::gestionar_subcuadras` pasara `sede` al contexto — estaba ausente).

**UX superadmin — `editar_municipio.html`:**
- Badge verde "🏛️ Sede configurada: lat, lon" cuando el municipio ya tiene coordenadas de sede cargadas. Antes los campos mostraban el valor pero no había indicador visual de estado.

---

## ✅ Resuelto — sesión 18 (2026-09-24)

- **Datalist cascade en `registrar_infraccion.html`**: `<datalist>` con `<input list>`. Evento `input` en lugar de `change`. `inputmode="numeric"` en altura. Auto-selección cuando hay una sola altura.
- **Menú hamburguesa — X en rojo al abrir**: `.menu-toggle.abierto span { background: #e74c3c }` en `global.css`.
- **Dark mode `historial_infracciones.html`**: colores hardcodeados reemplazados por variables CSS.
- **Flag `inspector_ve_sus_infracciones`** faltaba en contexto de `panel_inspectores`.
- **SIA `PATENTE_NO_COINCIDE` — mini-diálogo de confirmación**: "↩ No, corregir patente" vs "🚨 Sí, infraccionar igual", en lugar de solo mostrar error.
- **`ticket_infraccion.html` — solo opciones de impresión** después de generar acta.
- **BLE impresora — reconexión via `watchAdvertisements()`**: estrategia en 3 niveles para evitar desvinculación en copia 2.
- **Reintegro unificado en Módulos de pago**: eliminado bloque duplicado de ⚙️ Configuración general. Los campos aparecen dentro del card del módulo cuando está activo.
- **`btn-confirmar-est` siempre deshabilitado tras error POST**: función `_contexto_base()` garantiza contexto completo en todos los retornos de error. Auto-click del primer `.duracion-btn` al seleccionar vehículo.

---

## ✅ Resuelto — sesiones 13–17 (2026-09-20 al 2026-09-22)

- Mapa subcuadras roto en `/superadmin/` — Leaflet CSS/JS movidos a los blocks correctos.
- QR scan — infracción ya pagada/cancelada: se muestran infracciones recientes antes de permitir estacionar.
- Notificaciones → Sugerencias en panel conductor.
- Alerta saldo insuficiente antes de estacionar.
- Superadmin: gestión de tolerancia de multa + flag `admin_puede_configurar_tolerancia`.
- Comentarios Django visibles en templates → convertidos a `<!-- -->`.
- Flag `mapa_infracciones_activo` por municipio.
- Sidebar admin — items condicionales por flags (`puede_gestionar_subcuadras`, `mapa_infracciones_activo`).
- 403 con estilo en módulos deshabilitados.
- Seguridad: admin no puede administrar a otro admin/tesorero.
- Tabs Vendedores/Inspectores en `/admin-staff/` con sticky headers.
- Dashboard admin: "Cobros por vendedores" + sección "Infracciones por día".
- Importar exenciones — formato Excel real (6 columnas, `es_global` desde radio selector).
- `/pagar/` — confirmación de patente antes de buscar.
- Footer tutorial + sugerencias en todos los roles.
- Flag `modulo_informes_activo` + rediseño UX `/admin-rendiciones/`.
- Auditoría de reseteos de contraseña (`AuditoriaPassword`).
- `/admin-subcuadras/` habilitado para admin con flag de superadmin.
- BilleteraConductor (saldo por municipio).
- Mail automático al resetear contraseña al DNI.
- `panel_tesorero.html` — UX y bugs.
- Flujo confirmación depósito tesorero → vendedor.
- Refactor estilos inline → clases CSS (5 clases utilitarias, 84 reemplazos en 58 templates).
- 10 errores en tests corregidos.
- BLE impresora — duplicado no imprime + reconexión.
- Multi-vehículo simultáneo en inicio.
- Cards responsive en mis-infracciones, mis-estacionamientos.
