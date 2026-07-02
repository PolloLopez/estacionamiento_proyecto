# Pendiente — Estacionamiento Proyecto

Tareas pendientes ordenadas por prioridad. Actualizar cuando se resuelvan.

---

## 🔴 Alta prioridad

### 1. Doble alerta en vendedores/cobrar_abono.html
El template todavía tiene su propio `{% if messages %}` block además del que ya está en base.html.
Hay que eliminar el bloque del template (base.html lo maneja solo).
Archivo: `templates/vendedores/cobrar_abono.html`

### 2. Admin-usuarios: editar datos, cargar saldo, verificar
`/usuarios/admin-usuarios/` necesita poder:
- Modificar nombre, apellido, correo, telefono, numero_dni
- Cambiar es_verificado (toggle)
- Cargar saldo manualmente
- Agregar vehículo con tipo (auto/moto)

### 3. Comisiones — verificar que se muestran bien en caja vendedor
`/usuarios/vendedores/caja/` — los movimientos de infracciones cobradas deben aparecer
y el "Total a rendir" debe incluirlos. Verificar con datos reales.

---

## 🟡 Media prioridad

### 4. Inspector: rendición diaria a tesorería
Flujo nuevo: inspector entrega efectivo a tesorero al final del día.
Diferente al cierre de caja de vendedor.
Hay código parcial en el proyecto. Revisar y completar.
Requiere: nuevo template, view, URL, posiblemente nuevo modelo RendicionInspector.

### 5. Panel admin: rediseñar botones
Los botones del panel admin son chicos. Hacerlos más grandes y visuales,
similar a lo que se hizo en el panel inspector.
Archivo: `templates/admin/panel_admin.html`

### 6. admin_rendiciones: migrar a modelo Rendicion
La view `admin_rendiciones` usa el modelo viejo `CierreCaja`.
Hay un modelo nuevo `Rendicion` con estados pendiente/validada/observada
que todavía no se usa acá.
Archivo: `app_estacionamiento/views.py` → view `admin_rendiciones`

---

## 🟢 Baja prioridad / Futuras versiones

### 7. Inspector: foto con watermark y GPS
Al labrar acta, el inspector debería poder sacar foto desde el celular.
La foto debe incluir watermark (fecha, hora, GPS, patente) y grabarse en el acta.
Modelo Infraccion ya tiene campo foto (ImageField).
Dejar para v2 — requiere trabajo de UX móvil + backend de imágenes.

### 8. Inspector como cobrador de abonos mensuales (pago feature)
El inspector actualmente NO puede cobrar estacionamientos ni abonos.
Este podría ser un feature de pago (suscripción municipio).
Por ahora: disabled. Cuando se active, agregar "inspector" al decorator
de registrar_estacionamiento_vendedor y cobrar_abono.

### 9. Dividir views.py en módulos por rol
views.py tiene ~3200 líneas. Dividir en:
- views_admin.py
- views_conductor.py
- views_inspector.py
- views_vendedor.py
- views_tesorero.py
- views_mp.py (MercadoPago)
Mantener el mismo urls.py apuntando a los mismos nombres de función.
Hacer en un sprint dedicado — no mezclar con features.

### 10. Tests faltantes
Hay tests para flujos básicos pero faltan:
- Test abono mensual (cobro, verificación, conflicto mismo mes)
- Test tolerancia multa (pagar antes vs después del período)
- Test comisiones (que comision_monto se grabe correctamente)
- Test tesorero: depositar → vendedor certifica
- Test multi-municipio (datos aislados)
Ver: `tests/` en el proyecto

### 11. Completar perfil si municipio no se asigna en OAuth
Si hay más de un municipio activo, el middleware redirige a `completar_perfil`.
Esta view existe pero el template podría mejorar.
Testear con más de un municipio en DB.

---

## 📝 Deuda técnica conocida

- `Estacionamiento.duracion_min` almacena HORAS (no minutos). El nombre es engañoso
  pero NO se puede cambiar sin migration. Documentado en context.md.
- `precio_por_hora_moto = 0` significa "usar tarifa auto". No es intuitivo.
  Considerar cambiar a `null=True` en próxima migration grande.
- `gestionar_infracciones.html` — template viejo que ya no se renderiza. Eliminar.
- La función `puede_estacionar_ahora()` hace una query a HorarioEstacionamiento
  y otra a DiaEspecial. Si el tráfico crece, podría optimizarse con caché de 1 hora.
