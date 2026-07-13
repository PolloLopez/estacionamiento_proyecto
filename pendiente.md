# Pendiente — Estacionamiento Proyecto

Última actualización: 2026-07-02 (revisión completa contra código real)

---

## 🟡 Media prioridad


---

## 🟢 Baja prioridad / Futuras versiones

### 3. Inspector: foto con watermark y GPS
Al labrar acta el inspector saca foto desde el celular con watermark (fecha, hora, GPS, patente).
`Infraccion` ya tiene campo `foto` (ImageField). Dejar para v2.

### 4. Inspector como cobrador (paid feature)
Si se activa: agregar rol "inspector" al decorator de `registrar_estacionamiento_vendedor` y `cobrar_abono`.

### 5. Dividir views.py en módulos por rol
~3300 líneas. Dividir en `views_admin.py`, `views_conductor.py`, etc.
Hacer en un sprint dedicado — no mezclar con features.

### 6. Tests faltantes
- Abono mensual (cobro, verificación, conflicto mismo mes)
- Tolerancia multa (pagar antes vs después del período de gracia)
- Comisiones (que `comision_monto` se grabe correctamente)
- Tesorero: depositar → vendedor certifica
- Multi-municipio (datos aislados entre municipios)
- Flujo MP webhook (integración)

### 7. Mejoras OAuth y UI
- Pantalla de consentimiento Google: completar logo, descripción, dominio verificado
- Modo alto contraste / uso en exterior con sol
- Separar `settings_dev.py` / `settings_prod.py`

---

## ✅ Resuelto

- Inspector PDF del día: `pdf_infracciones_hoy` con reportlab — descarga PDF con acta/hora/patente/subcuadra/motivo/monto/estado; soporta `?fecha=YYYY-MM-DD`; botón "📄 PDF del día" en panel inspector
- Google OAuth nombre/apellido: middleware detecta `first_name` vacío en conductores y redirige a `completar_perfil`; el form acepta nombre/apellido + municipio de forma independiente según lo que falte
- Timer "calculando…" indefinido: `inicio_usuarios.html` estaba truncado, faltaba `setInterval`. Corregido con el bloque JS completo.
- Subcuadras vacías al registrar infracción: `get_subcuadra_default` usa `get_or_create("Zona Única")` — nunca falla.
- /usuarios/inicio/ rompe con conductor: verificado en código — la view maneja `None` municipio correctamente. Sin reproducción desde 2026-06-10.
- Selector de período al cerrar caja: modal con `<select>` diario/semanal/mensual, field `CierreCaja.periodo`, migration 0038, `generar_cierre_caja(periodo=...)`, historial muestra `get_periodo_display`
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
- CSRF: `CSRF_TRUSTED_ORIGINS=https://estacionamiento.up.railway.app` en Railway vars
- SITE_ID=2 en Railway vars (confirmado por usuario)
- Google OAuth `redirect_uri_mismatch`: nuevo cliente OAuth + URI autorizada
- Branding por municipio (logo + colores + nombre_sistema)
- Menú hamburguesa, botones sin estilo, 403.html, NoReverseMatch caja_inspector
