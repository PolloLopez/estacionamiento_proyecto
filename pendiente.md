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
Requiere: view nueva, template, posiblemente usar modelo Rendicion existente.
Actualmente `/usuarios/admin-rendiciones/` usa CierreCaja (vendedores), no tiene flujo de admin→tesorero.

---

## 🟡 Media prioridad

### 5. Vendedor caja: mostrar movimientos de infracciones
`/usuarios/vendedores/caja/` — los movimientos de infracciones cobradas deben aparecer
y el "Total a rendir" debe incluirlos.

### 6. Tesorería: mostrar rendiciones recibidas
Panel tesorero debe mostrar las rendiciones que le han hecho (qué recibió, cuándo, de quién).
View: `panel_tesorero` — agregar query de CierreCaja certificados + Rendicion del municipio.

### 7. Inspector: PDF de infracciones del día
El inspector "presenta" sus infracciones del día como PDF (no rinde dinero).
PDF con listado ordenado por número de acta: fecha, patente, tipo, subcuadra, monto, estado.
Requiere: view que filtra por inspector+fecha, genera PDF, botón en "Mis infracciones".

### 8. admin_rendiciones: migrar a modelo Rendicion
La view `admin_rendiciones` usa el modelo viejo `CierreCaja`.
Hay un modelo nuevo `Rendicion` que todavía no se usa acá.

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

## ✅ Resuelto esta sesión

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
