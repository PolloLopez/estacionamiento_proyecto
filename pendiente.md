# Pendiente — Estacionamiento Proyecto

Tareas pendientes ordenadas por prioridad. Actualizar cuando se resuelvan.

---

## 🔴 Alta prioridad

### 1. Doble alerta en vendedores/cobrar_abono.html
El template todavía tiene su propio `{% if messages %}` block además del que ya está en base.html.
Hay que eliminar el bloque del template (base.html lo maneja solo).
Archivo: `templates/vendedores/cobrar_abono.html` — líneas 11-16

### 2. Admin-usuarios: editar datos, cargar saldo, verificar
`/usuarios/admin-usuarios/` necesita poder:
- Modificar nombre, apellido, correo, telefono, numero_dni
- Cambiar es_verificado (toggle)
- Cargar saldo manualmente
- Agregar vehículo con tipo (auto/moto)

### 3. Abono mensual: selector de mes
`/usuarios/vendedores/abono/` permite cobrar solo el mes actual.
El vendedor debe poder elegir el mes a abonar (por ejemplo si paga enero de forma anticipada
o si la municipalidad acepta pago atrasado).
Agregar un `<select>` de mes al formulario de búsqueda.
View: `cobrar_abono` — `mes_actual = hoy.replace(day=1)` hardcodeado, debe venir del POST.

---

## 🟡 Media prioridad

### 4. Vendedor caja: mostrar movimientos de infracciones
`/usuarios/vendedores/caja/` — los movimientos de infracciones cobradas deben aparecer
y el "Total a rendir" debe incluirlos.
View: `caja_inspector` (compartida con vendedor) — verificar filtros.

### 5. Tesorería: mostrar rendiciones recibidas
Panel tesorero debe mostrar las rendiciones que le han hecho (qué recibió, cuándo, de quién).
View: `panel_tesorero` — agregar query de CierreCaja certificados del municipio.

### 6. Inspector: PDF de infracciones del día
El inspector "presenta" sus infracciones del día como PDF (no rinde dinero, no cobra).
PDF con listado ordenado por número de acta: fecha, patente, tipo, subcuadra, monto, estado.
Requiere: view que filtra por inspector+fecha, genera PDF con la skill pdf, botón en "Mis infracciones".

### 7. Panel admin: rediseñar botones
Los botones del panel admin son chicos. Hacerlos más grandes y visuales.
Archivo: `templates/admin/panel_admin.html`

### 8. admin_rendiciones: migrar a modelo Rendicion
La view `admin_rendiciones` usa el modelo viejo `CierreCaja`.
Hay un modelo nuevo `Rendicion` que todavía no se usa acá.

---

## 🟢 Baja prioridad / Futuras versiones

### 9. Inspector: foto con watermark y GPS
Al labrar acta, el inspector debería poder sacar foto desde el celular.
La foto debe incluir watermark (fecha, hora, GPS, patente).
Modelo Infraccion ya tiene campo foto (ImageField). Dejar para v2.

### 10. Inspector como cobrador (paid feature)
El inspector actualmente NO puede cobrar estacionamientos ni abonos.
Podría ser un feature de pago futuro. Por ahora: disabled.
Si se activa: agregar "inspector" al decorator de registrar_estacionamiento_vendedor y cobrar_abono.

### 11. Dividir views.py en módulos por rol
views.py tiene ~3200 líneas. Dividir en:
- views_admin.py, views_conductor.py, views_inspector.py, views_vendedor.py, views_tesorero.py, views_mp.py
Mantener el mismo urls.py apuntando a los mismos nombres de función.
Hacer en un sprint dedicado — no mezclar con features.

### 12. Tests faltantes
- Test abono mensual (cobro, verificación, conflicto mismo mes)
- Test tolerancia multa (pagar antes vs después del período)
- Test comisiones (que comision_monto se grabe correctamente)
- Test tesorero: depositar → vendedor certifica
- Test multi-municipio (datos aislados)

### 13. Completar perfil si hay más de un municipio activo
Middleware redirige a completar_perfil. Mejorar UX del template.

---

## 📝 Deuda técnica conocida

- `Estacionamiento.duracion_horas` — campo renombrado de duracion_min. El nombre viejo era
  engañoso (almacenaba horas). Ya corregido en migration 0036.
- `precio_por_hora_moto = null` — null significa "usar tarifa de auto". Ya corregido en 0037.
- `puede_estacionar_ahora()` — ya tiene caché de 1 hora. ✅
- `gestionar_infracciones.html` — eliminado. ✅
