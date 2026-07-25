# testeo.md — Checklist de validación

Última actualización: 2026-07-22

---

## 1. Tests automáticos

```bash
python manage.py test app_estacionamiento --verbosity=2
```

Resultado esperado: **89 tests, 0 failures**

Archivos de tests:
- `tests.py` — tests generales (flujos, roles, PDF, caja)
- `tests_roles.py` — tests de permisos por rol + flujo completo conductor
- `tests_servicios.py` — tests de services: infracciones, saldo, abono, comisiones, multi-municipio, tesorero, tolerancia multa, watermark, subcuadra, exento parcial

---

## 2. Validación Django

```bash
python manage.py check
python manage.py makemigrations --check
```

Resultado esperado: sin issues, sin migraciones pendientes.

---

## 3. Test manual — Tolerancia de gracia (feature nueva)

**Setup previo:** en el admin del municipio, configurar `tolerancia_multa_minutos = 5`.

### Caso A — pago dentro del período de gracia

1. Loguearse como **inspector** → registrar infracción a un vehículo del conductor de prueba
2. Loguearse como **conductor** dueño de ese vehículo → ir a "Mis infracciones"
3. Dentro de los primeros 5 minutos de creada la infracción:
   - El botón "💳 Pagar con saldo" abre un modal con encabezado **"✅ Período de gracia"**
   - Dice: "La infracción se anulará sin costo"
   - Botón: **"Anular sin costo"**
4. Confirmar → la infracción pasa a estado **"Anulada"**, el saldo no se mueve

### Caso B — pago fuera del período de gracia

1. Mismos pasos, pero esperar más de 5 minutos (o setear `tolerancia_multa_minutos = 0` para forzar)
2. Al abrir el modal:
   - Encabezado: **"⚠️ Pago fuera de término"**
   - Caja amarilla: "Estás pagando fuera del período de gracia (5 min). Se descontarán $X de tu saldo."
   - Botón rojo: **"Pagar $X"**
3. Confirmar → la infracción pasa a **"Pagada"** y el saldo se descuenta

### Caso C — cancelar sin pagar

En cualquier modal (A o B): presionar **"Cancelar"** → el modal se cierra, no pasa nada.

### Caso D — saldo insuficiente

Si el conductor no tiene saldo suficiente: el botón "Pagar con saldo" no aparece, se muestra "Saldo insuficiente".

---

## 4. Test manual — Flujos base

### Conductor
- Login → estacionar → finalizar → consultar historial
- Agregar vehículo nuevo → estacionar con ese vehículo
- Sin saldo → intentar estacionar → redirige a cargar saldo (MercadoPago)

### Inspector
- Seleccionar subcuadra en el dropdown → verificar patente → confirmar que el estado es correcto
- Registrar infracción con foto: la foto debe aparecer en el ticket con watermark (patente, inspector, subcuadra, GPS o "sin señal", fecha/hora)
- Registrar infracción SIN GPS disponible: watermark igual debe aparecer con "GPS: sin señal"
- Ticket: NO se imprime automáticamente. El inspector debe ver la foto y hacer clic en "Imprimir acta"
- Ver PDF de infracciones del día

### Vendedor
- Cobrar estacionamiento manual
- Cobrar abono mensual → verificar que no se puede cobrar el mismo mes dos veces
- Cerrar caja → ver comisión calculada

### Admin
- Cargar saldo a conductor
- Gestionar tarifas (precio hora auto/moto, abono)
- Gestionar exenciones (total/parcial)
- Crear rendición y enviar a tesorero

### Tesorero
- Ver rendiciones pendientes
- Depositar comisión a vendedor
- Vendedor certifica recibo
