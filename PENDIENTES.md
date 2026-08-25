# Pendientes — Estacionamiento Proyecto

Última actualización: 2026-08-24

---

## 🗺️ Contexto de deploy

- **Railway** → ambiente de prueba (inspectores + admin testeando). No es producción municipal real.
- **Digital Ocean** → deploy definitivo cuando el sistema vaya a municipios reales pagando.
- El código es el mismo; los cambios son de infraestructura y configuración.

---

## 🔴 Alta prioridad

### Migración pendiente de correr en Railway
```
python manage.py makemigrations --name="sia_titular_fields_vehiculo"
python manage.py migrate
```
Agrega `sia_titular_nombre`, `sia_titular_apellido`, `sia_titular_dni`, `sia_nci` a `Vehiculo`.
Ya está en el modelo; falta correrla en producción.

### Auditorías — correr todas antes del próximo municipio real
Las auditorías se corrieron en julio/agosto temprano. El sistema creció mucho desde entonces.
Correrlas nuevamente antes de cualquier go-live:
- `auditoria-seguridad` — especialmente por el agregado de endpoints públicos y OAuth
- `auditoria-rendimiento` — por el crecimiento de datos y nuevas queries en el admin
- `auditoria-base-datos` — validar normalización de los nuevos campos SIA + campos de perfil
- `checklist-produccion` — antes de cualquier entrega a municipio real

---

## 🟡 Media prioridad

### Reseteo de contraseña desde el panel admin
Admin hace clic en "Resetear contraseña" en la ficha del usuario → envía link de reset por email
→ el usuario debe cambiar al primer login.
Requiere:
- `cambio_password_requerido = BooleanField(default=False)` en `Usuario` + migración
- Acción en la vista de detalle de usuario (admin)
- Check en `login_view` que redirija al formulario de cambio si el flag está activo

### Comisión vendedor como feature premium
- Hoy `comision_vendedor` aplica a todos los municipios. Debería ser un módulo que el superadmin activa.
- Admin solo ve la sección "Comisiones" en tarifas si el módulo está habilitado para su municipio.
- Toggle por vendedor individual (algunos vendedores no cobran comisión).

### Perfil extendido — Vendedor
Campos nuevos en `Usuario` (requieren migración):
- `telefono_particular`, `telefono_comercial`, `domicilio_comercial` (CharField)
- `horarios_atencion` (JSONField) — días y franjas horarias de atención
- `ubicacion_lat`, `ubicacion_lon` (DecimalField) — para mapa y búsqueda del más cercano

### Perfil extendido — Conductor
- `domicilio` (CharField) — fundamental para identificar frentistas

### Tesorero como fallback para certificar cierres de admin
`certificar_cierre` es `@require_role("admin")`. Si el único admin no puede autocertificarse,
el tesorero necesita poder certificar cierres de admin como válvula de escape.
Falta: listado en panel tesorero de cierres de admin sin certificar + acción para certificarlos.

### Cierre de caja configurable por período
- Frecuencia esperada configurable (diaria/semanal/mensual) por municipio o por vendedor.
- Semáforo en panel admin: vendedores atrasados en cerrar caja.
- Admin puede forzar el cierre de un vendedor (ausencia o imprevisto).

### Panel de auditoría del superadmin
Vista global: total recaudado/rendido/pendiente por municipio.
(El panel de auditoría interno del admin ya está: `auditoria_staff`)

### Ícono PWA dinámico (logo del municipio)
El `manifest.json` es estático. Debería servirse dinámicamente con el logo del municipio.
No testeable en local — requiere HTTPS (Railway o ngrok).

### Reportes de subcuadras (dashboard de cobertura)
Dashboard por subcuadra: verificaciones / infracciones / vehículos exentos en el período.
Datos ya existen: `VerificacionInspector` + `Infraccion` + `Vehiculo.subcuadras_exentas`.

---

## 🟢 Baja prioridad / Futuras versiones

### GitHub Pages: reemplazar landing_estacionar.html
La `landing.html` del sistema Django **sí sirve** para GitHub Pages con dos cambios mínimos:
1. Eliminar la primera línea: `{% load static %}`
2. Reemplazar los dos `{% url 'pago_publico_buscar' %}` por `https://estacionamiento.up.railway.app/pagar/`

Todo lo demás es HTML/CSS autocontenido (sin herencia de base.html, sin assets externos propios).
El resultado puede reemplazar directamente `landing_estacionar.html` en el repo de GitHub Pages.

### Responsive > 1050px
En pantallas grandes el layout del panel admin queda con mucho espacio vacío.

### Migración a Digital Ocean (producción municipal real)
**Disparador**: cuando el sistema pase de pruebas a municipio real pagando.
Ver checklist: `CHECKLIST_PRODUCCION_2026-07-25.md`.

### Inspector como cobrador (configurable por municipio)
Toggle por superadmin via `ModuloMunicipio`.

### Transferencia de saldo entre usuarios
`TransferenciaSaldo` (emisor, receptor, monto, estado). Receptor tiene 24h para aceptar.

### Reconocimiento de patente por cámara (OCR)
Google ML Kit o Tesseract.js. Botón "📷 Escanear" en `verificar.html`.

### Alertas de vencimiento al conductor (push / WhatsApp)

### Mapa de calor de infracciones
Leaflet.js + lat/lon de subcuadras (coordenadas ya en el modelo).

### Módulo de impugnaciones
`Impugnacion` (infraccion, conductor, motivo, evidencia, estado). Admin resuelve desde panel.

### Dashboard en TV (pantalla municipal en tiempo real)
Vista sin login con token de solo lectura. Auto-refresh cada 60s.

### Toggle estadísticas de inspectores por municipio
`Municipio.estadisticas_inspectores_activo = BooleanField(default=True)`. 1 migración, 1 chequeo.

### Tutorial de uso — GIFs en landing pública
El tutorial por rol ya está dentro del sistema (collapsible `<details>` en cada panel).
Pendiente: versión con GIF animado o screenshots para la landing pública.

---

## ✅ Resuelto recientemente

**Sesión 2026-08-24 (tarde)** — Tarifas click-to-edit, login UX, lockout reset link:
- Login: `login_view` detecta tipo de error y lo pasa al template (`correo_no_encontrado`, `password_incorrecta`, `cuenta_inactiva`, `campos_vacios`). `<details>` se abre automáticamente. Input borde rojo en campo fallido. Correo se pre-carga. ✅
- Lockout: botón "🔑 Restablecer contraseña" → `/accounts/password/reset/`. ✅
- Tarifas refactorizadas a 7 secciones individuales (una por campo). Cada POST actualiza un solo valor. ✅
- Tarifas click-to-edit: modo lectura por defecto, ✏️ Editar abre input inline, confirmación muestra solo ese campo (valor viejo → nuevo). Dialog centrado correctamente con `position:fixed + transform`. ✅
- Partial `admin/_campo_tarifa.html` reutilizable. ✅
- Test actualizado: secciones individuales + verificación de aislamiento entre campos. ✅

**Sesión 2026-08-24 (mañana)** — SIA parser v2, titular SIA, sidebar agrupado, exenciones unificadas:
- SIA parser: fix raíz — ANDIS usa `<th>` en encabezados. Si hay `<th>` → Strategy B. 38 tests OK. ✅
- `ResultadoSia` con `nombre`, `apellido`, `documento` separados. Parser extrae DNI del titular. ✅
- `Vehiculo`: campos `sia_titular_nombre`, `sia_titular_apellido`, `sia_titular_dni`, `sia_nci`. Migración pendiente. ✅
- `views_inspector.verificar_sia`: guarda nombre, apellido, DNI y NCI al verificar SIA válido. ✅
- Modal inspector: botón "↩ Verificar otro" + auto-reset a los 5s si SIA fue exitoso. ✅
- Sidebar admin agrupado en 4 rubros: Personal · Vehículos · Configuración · Caja y rendiciones. ✅
- Exenciones unificadas: badge "♿ SIA · ANDIS" en búsqueda y lista global con nombre, DNI, vigencia coloreada. ✅

**Sesión 2026-08-23** — Dark mode, responsive, SIA parser fix inicial, auditoría staff, cierre de caja admin:
- Dark mode toggle en navbar (persiste en `localStorage`). FOUC prevention. `--color-acento`. ✅
- `Municipio.color_acento` (migración 0055). Superadmin configura 3 colores. ✅
- Responsive completo: doble padding fix, grid admin colapsable, tablas con overflow-x. ✅
- `auditoria_staff`: vista unificada admin con vendedores e inspectores. URL `admin-staff/`. ✅
- Cierre de caja para rol admin: URL `admin/cerrar-caja/`. ✅

**Sesión 2026-08-21** — OAuth account takeover + SIA ANDIS + bloqueo fuera de horario:
- `adapters.py`: `pre_social_login()` bloquea auto-connect si el email ya existe sin cuenta Google. ✅
- `services/sia_verificacion.py`: verificación SIA contra ANDIS. Validación SSRF, parseo HTML, 8 estados. ✅
- `models.py`: campos `sia_*` en `Infraccion` (migración 0054). ✅
- `views_inspector.py`: bloquea infraccionamiento fuera del horario de cobro. ✅

**Sesión 2026-08-18/20** — MercadoPago, backups, seguridad, email, tarifas:
- Pago público sin registro: `PagoPublico` (migración 0051), webhook, 4 templates. ✅
- Backups PostgreSQL: workflow GitHub Actions diario → artifact 30 días. Restore testado. ✅
- Email transaccional (Brevo/anymail): recuperación de contraseña funcionando. ✅
- `django-axes`: lockout combinado IP+usuario, 5 intentos, 1h cooloff. ✅
- Verificación de email obligatoria en Railway (`ACCOUNT_EMAIL_VERIFICATION=mandatory`). ✅
- Límites de carga MercadoPago configurables por municipio (migración 0052). ✅
- `gestionar_tarifas`: fix `MultipleObjectsReturned`, auto-limpia duplicados. ✅
- 160 tests, todos OK. ✅

**Sesiones 2026-08-13/19** — GPS, subcuadras, superadmin, impresora BLE, rendiciones:
- `Subcuadra.lat/lon` + endpoint GPS. ✅
- Superadmin `editar_municipio`: logo, colores, `leyenda_horarios`, `texto_ordenanza` (migraciones 0053). ✅
- Importación de exenciones desde Excel. ✅
- `PlantillaDocumento` (5 tipos de comprobante personalizables). ✅
- Impresora BLE: persistencia en `localStorage`, doble copia automática, QR nativo ESC/POS. ✅
- Rendiciones: PDF, tesorero valida/observa, `LiquidacionComision` con factura. ✅
- PWA icons reales (192, 512, apple-touch). ✅
