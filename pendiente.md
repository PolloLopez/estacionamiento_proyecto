# Pendiente — Estacionamiento Proyecto

Tareas pendientes ordenadas por prioridad. Actualizar cuando se resuelvan.

---

## 🔴 Alta prioridad

### 1. Doble alerta en vendedores/cobrar_abono.html
El template todavía tiene su propio `{% if messages %}` block además del que ya está en base.html.
Archivo: `templates/vendedores/cobrar_abono.html` — líneas 11-16

### 2. Admin-usuarios: editar datos, cargar saldo, verificar
`/usuarios/admin-usuarios/` necesita poder:
- Cambiar es_verificado (toggle)
- Ver telefono, numero_dni en el detalle

### 3. Abono mensual: selector de mes
`/usuarios/vendedores/abono/` — el vendedor debe poder elegir el mes a abonar.
Agregar `<select>` de mes al formulario. View: `cobrar_abono` — `mes_actual` hardcodeado.

### 4. Admin rendición a tesorería (nuevo flujo)
El admin cierra un período y rinde a tesorería con desglose por tipo de pago:
- Cuánto en efectivo
- Cuánto por cada medio digital (sistema / tarjeta / transferencia)
Modelo `Rendicion` YA EXISTE con todos los campos necesarios (fecha_desde/hasta, total_efectivo,
total_digital, total_comisiones, total_neto, estado, notas_tesorero).
`panel_tesorero` YA muestra las Rendicion del municipio — solo falta la view de creación.
Requiere: view `crear_rendicion` (admin POST) + URL + template.
`admin_rendiciones` sigue siendo CierreCaja (vendedor→admin) — correcto, no tocar.

### 5. Doble alerta en resumen_caja.html y panel_tesorero.html
Mismo patrón que el ya resuelto en detalle_usuario.html: tienen su propio `{% if messages %}`
que duplica el de base.html.
- `templates/vendedores/resumen_caja.html` — líneas 20-25
- `templates/tesorero/panel_tesorero.html` — líneas 11-16

---

## 🟡 Media prioridad

### 6. Inspector: PDF de infracciones del día
El inspector "presenta" sus infracciones del día como PDF (no rinde dinero).
PDF con listado ordenado por número de acta: fecha, patente, tipo, subcuadra, monto, estado.
Requiere: view que filtra por inspector+fecha, genera PDF, botón en "Mis infracciones".

---

## 🟢 Baja prioridad / Futuras versiones

### 9. Inspector: foto con watermark y GPS
Al labrar acta, el inspector saca foto desde el celular con watermark (fecha, hora, GPS, patente).
Modelo Infraccion ya tiene campo foto (ImageField). Dejar para v2.

### 10. Inspector como cobrador (paid feature)
Si se activa: agregar "inspector" al decorator de registrar_estacionamiento_vendedor y cobrar_abono.

### 11. Dividir views.py en módulos por rol
views.py tiene ~3200 líneas. Dividir en views_admin.py, views_conductor.py, etc.
Hacer en un sprint dedicado — no mezclar con features.

### 12. Tests faltantes
- Test abono mensual (cobro, verificación, conflicto mismo mes)
- Test tolerancia multa (pagar antes vs después del período)
- Test comisiones (que comision_monto se grabe correctamente)
- Test tesorero: depositar → vendedor certifica
- Test multi-municipio (datos aislados)

---

## ✅ Resuelto esta sesión (hoy)

- Admin rendición a tesorería: view `crear_rendicion` + URL + template `crear_rendicion.html`
  Modelo `Rendicion` ya existía; panel_tesorero ya la muestra. Solo faltaba el formulario de creación.
- Doble alert eliminado: `cobrar_abono.html`, `resumen_caja.html`, `panel_tesorero.html`, `rendiciones.html`
- `certificar_comision` restaurada (estaba truncada en working copy por desfase mount Windows/Linux)
- Vendedor caja: infracciones ya aparecen (`cobrar_infraccion_vendedor` crea MovimientoCaja)
- Tesorería rendiciones: `panel_tesorero` ya muestra modelo `Rendicion` — template completo
- admin_rendiciones: usa CierreCaja (vendedor→admin) — correcto, no necesita migración
- `gestionar_infracciones.html` eliminado
- `puede_estacionar_ahora()` con caché de 1 hora
- `duracion_min` → `duracion_horas` (migration 0036)
- `precio_por_hora_moto` → null=True (migration 0037)
- Procfile: `migrate` antes de `gunicorn` — migraciones automáticas en deploy
- Panel inspector: solo "Infracciones hoy" + Verificar + Mis infracciones
- panel_admin: sin tabla de estacionamientos; stat "Conductores registrados"
- inicio_admin: redirige a panel_admin (no mostraba nada)
- detalle_usuario: doble alert eliminado, infracciones últimas 5 + "Ver todas",
  responsive en tabla vehículos, tipo en agregar vehículo
- CSRF fix: agregar CSRF_TRUSTED_ORIGINS=https://estacionamiento.up.railway.app en Railway vars
