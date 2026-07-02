# Pendiente — Estacionamiento Proyecto

Última actualización: 2026-07-02

---

## 🔴 Alta prioridad

### 1. Selector de período al cerrar caja (vendedor)
`/usuarios/vendedores/cerrar-caja/` — `cerrar_caja` no pide período.
El modelo `CierreCaja` tiene campo `periodo` (diario/semanal/mensual) pero no se usa.
Requiere: `<select>` en el form de cierre + guardarlo en el cierre.

### 3. Selector de período al cerrar caja (vendedor)
`/usuarios/vendedores/cerrar-caja/` — `cerrar_caja` no pide período.
El modelo `CierreCaja` tiene campo `periodo` (diario/semanal/mensual) pero no se usa.
Requiere: `<select>` en el form de cierre + guardarlo en el cierre.

---

## 🟡 Media prioridad

### 4. Inspector: PDF de infracciones del día
El inspector "presenta" sus infracciones del día como PDF.
Listado ordenado por número de acta: fecha, patente, tipo, subcuadra, monto, estado.
Requiere: view + PDF generation + botón en "Mis infracciones".

### 5. Google OAuth: nombre y apellido no se cargan
Usuario creado por Google OAuth no guarda `first_name` / `last_name` correctamente.
Al ingresar por primera vez con Google, redirigir a `completar_perfil`.
Requiere: adapter de allauth o signal `user_signed_up`.

### 6. Subcuadras vacías al registrar infracción
`registrar_infraccion` usa `get_subcuadra_default()` — si el municipio no tiene subcuadras
cargadas, la view muestra error y el inspector no puede labrar acta.
Requiere: verificar si hay subcuadras en producción o mejorar el manejo del caso vacío.

### 7. /usuarios/inicio/ rompe cuando conductor está logueado
Reportado en PENDIENTES.md (2026-06-10). Verificar si sigue ocurriendo con la versión actual.
View: `inicio_usuarios`.

### 8. Timer en inicio_usuarios muestra "calculando…" indefinido
El JS usa `hora_inicio|date:"U"` (Unix timestamp). Si hay problema de zona horaria
el `new Date(ts * 1000)` puede dar un fin ya pasado o incorrecto.
Template: `templates/usuarios/inicio_usuarios.html` línea 57.

---

## 🟢 Baja prioridad / Futuras versiones

### 9. Inspector: foto con watermark y GPS
Al labrar acta el inspector saca foto desde el celular con watermark (fecha, hora, GPS, patente).
`Infraccion` ya tiene campo `foto` (ImageField). Dejar para v2.

### 10. Inspector como cobrador (paid feature)
Si se activa: agregar rol "inspector" al decorator de `registrar_estacionamiento_vendedor` y `cobrar_abono`.

### 11. Dividir views.py en módulos por rol
~3256 líneas. Dividir en `views_admin.py`, `views_conductor.py`, etc.
Hacer en un sprint dedicado — no mezclar con features.

### 12. Tests faltantes
- Abono mensual (cobro, verificación, conflicto mismo mes)
- Tolerancia multa (pagar antes vs después del período de gracia)
- Comisiones (que `comision_monto` se grabe correctamente)
- Tesorero: depositar → vendedor certifica
- Multi-municipio (datos aislados entre municipios)
- Flujo MP webhook (integración)

### 13. Mejoras OAuth y UI
- Pantalla de consentimiento Google: completar logo, descripción, dominio verificado
- Modo alto contraste / uso en exterior con sol
- Separar `settings_dev.py` / `settings_prod.py`

---

## ✅ Resuelto

- Abono mensual: selector de mes — 4 opciones (2 atrás, actual, siguiente), validación por mes elegido
- Admin-usuarios: editar teléfono, DNI, toggle es_verificado + badge en detalle

- Admin rendición a tesorería: view `crear_rendicion` + URL + template con cálculo en tiempo real
- Doble alert: `cobrar_abono.html`, `resumen_caja.html`, `panel_tesorero.html`, `rendiciones.html`
- `certificar_comision`: restaurada (estaba truncada en working copy)
- Cobrar infracciones por patente: `cobrar_infraccion_vendedor` completo y crea `MovimientoCaja`
- Tesorería rendiciones: `panel_tesorero` ya muestra `Rendicion` — template completo
- `gestionar_infracciones.html` eliminado
- `puede_estacionar_ahora()` con caché de 1 hora
- `duracion_min` → `duracion_horas` (migration 0036)
- `precio_por_hora_moto` → null=True (migration 0037)
- Procfile: `migrate --noinput` antes de `gunicorn`
- Panel inspector: solo "Infracciones hoy" + Verificar + Mis infracciones (sin dinero)
- panel_admin: sin tabla de estacionamientos; stat "Conductores registrados"
- inicio_admin: redirige a panel_admin
- detalle_usuario: doble alert eliminado, infracciones últimas 5 + "Ver todas", responsive + tipo vehículo
- CSRF: agregar `CSRF_TRUSTED_ORIGINS=https://estacionamiento.up.railway.app` en Railway vars
- SITE_ID=2 en Railway vars (confirmado por usuario)
- Google OAuth `redirect_uri_mismatch`: nuevo cliente OAuth + URI autorizada
- Branding por municipio (logo + colores + nombre_sistema)
- Menú hamburguesa, botones sin estilo, 403.html, NoReverseMatch caja_inspector
