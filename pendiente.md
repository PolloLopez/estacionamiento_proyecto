# Pendiente — Estacionamiento Proyecto

Última actualización: 2026-07-13

---

## 🟡 Media prioridad

### 5. Limpiar imports huérfanos en views.py
El facade `views.py` aún tiene el bloque de imports del legacy (servicios, utils, factories, etc.)
que ya no sirven desde que todo se movió a submódulos.
Antes de limpiar, confirmar que nada externo los use.

### 6. Tests faltantes (coverage incompleto)
- Tolerancia multa (pagar antes vs después del período de gracia) — `pagar_infraccion` use case
- Flujo MP webhook (integración)

---

## 🟢 Baja prioridad / Futuras versiones

### 7. Evaluar migración a Digital Ocean
Railway conveniente pero con limitaciones de costo/control a largo plazo.
**Disparador**: cuando el sistema tenga usuarios reales pagando.

### 8. Inspector: foto con watermark y GPS (v2)
`Infraccion` ya tiene campo `foto` (ImageField). La marca de agua GPS ya está implementada
en `services/infracciones.py::_agregar_marca_de_agua_gps`. Falta integrar en el flujo mobile.

### 9. Inspector como cobrador (paid feature)
Agregar rol "inspector" al decorator de `registrar_estacionamiento_vendedor` y `cobrar_abono`.

### 10. Mejoras OAuth y UI
- Pantalla de consentimiento Google: completar logo, descripción, dominio verificado
- Modo alto contraste / uso en exterior con sol
- Separar `settings_dev.py` / `settings_prod.py`

---

## ✅ Resuelto

### Alta prioridad — tests pre-existentes ✅
58 tests pasando (16 roles + 42 generales). Fixes aplicados:
- `Tarifa.objects.create` en `BaseRolesTest.setUp()` + `from decimal import Decimal`
- `crear_conductor()` con `first_name="Test"` (evita redirect middleware)
- `REDIRECT_OK = "inicio_usuarios"` en `use_cases/estacionar_vehiculo.py`

### Decisión de negocio: conductor sin verificar puede pagar infracciones ✅
El conductor busca infracciones por patente, sin requerir verificación.
No hay restricción a implementar.

### reportlab instalado localmente ✅
`pip install reportlab==4.2.5`

### TRAMA Sprint 1 — Dividir views.py en módulos por rol ✅
`views.py` pasó de ~3462 líneas a **156 líneas** (facade puro).
- `views_auth.py` (204 líneas) — login, logout, registro, completar_perfil
- `views_inspector.py` (384 líneas) — panel, verificación, infracciones, PDF
- `views_tesorero.py` (81 líneas) — panel tesorero, rendiciones
- `views_vendedor.py` (782 líneas) — cobros, caja, comisiones
- `views_conductor.py` (673 líneas) — estacionar, historial, vehículos
- `views_admin.py` (1033 líneas) — gestión completa del municipio
- `views_mp.py` (286 líneas) — integración MercadoPago

### TRAMA Sprint 2 — Lógica de negocio a services/ ✅
Creada la carpeta `services/` con módulos por dominio:
- `services/caja.py` — `generar_cierre_caja()`
- `services/infracciones.py` — `crear_infraccion()` + nuevo `cobrar_infraccion_efectivo()`
- `services/verificacion.py` — `verificar_estado_vehiculo()`
- `services/horarios.py` — `puede_estacionar_ahora()`, `calcular_opciones_duracion()`, `cerrar_estacionamientos_vencidos_por_horario()`
- `services/saldo.py` — nuevo `cargar_saldo_conductor()`

`utils.py` quedó en 32 líneas (solo `get_subcuadra_default`).
Los archivos `services_*.py` viejos son shims de 4 líneas para compatibilidad hacia atrás.

### TRAMA Sprint 3 — Consolidar use_cases/ con services/ ✅
- `services/horarios.py` → nueva `obtener_tarifa_hora(tarifa_obj, vehiculo)` (centraliza selección auto/moto)
- `services/saldo.py` → nueva `debitar_saldo_conductor(conductor, monto, descripcion)` (sin transacción propia)
- `services/caja.py` → nueva `registrar_cobro_efectivo(cobrador, monto, descripcion, comision_monto)`
- `use_cases/estacionar_vehiculo.py` 93→76 líneas
- `use_cases/pagar_infraccion.py` 73→64 líneas
- `use_cases/cobrar_estacionamiento.py` 37→23 líneas
- `test_roles.py` (duplicado viejo) eliminado — `tests_roles.py` lo cubre completo

### Tests faltantes cubiertos (tests_servicios.py) ✅
20 tests en 5 clases: `cobrar_infraccion_efectivo`, `cargar_saldo_conductor`,
abono mensual, comisiones, multi-municipio, tesorero→depositar→certificar.

### Otros ✅
- `test_conductor_sin_saldo_redirige_a_carga_mp`: test corregido (assertions a `mp_iniciar_carga`)
- Inspector PDF del día: `pdf_infracciones_hoy` con reportlab
- Google OAuth nombre/apellido: middleware + completar_perfil
- Timer "calculando…" indefinido: corregido
- Subcuadras vacías al registrar infracción: `get_or_create("Zona Única")`
- Selector de período al cerrar caja: modal + field `CierreCaja.periodo` + migration 0038
- Banner modo desarrollo
- Deprecation warnings allauth 65.x
- Abono mensual: selector de mes con 4 opciones
- Admin-usuarios: editar teléfono, DNI, toggle es_verificado
- Admin rendición a tesorería: view + URL + template
- Cobrar infracciones por patente: `cobrar_infraccion_vendedor` + `MovimientoCaja`
- Tesorería rendiciones: `panel_tesorero` + template
- `puede_estacionar_ahora()` con caché de 1 hora
- `duracion_min` → `duracion_horas` (migration 0036)
- `precio_por_hora_moto` → null=True (migration 0037)
- Procfile: `migrate --noinput` antes de `gunicorn`
- Panel inspector: sin dinero, solo infracciones + verificar
- CSRF: `CSRF_TRUSTED_ORIGINS` en Railway
- SITE_ID=2 en Railway
- Google OAuth `redirect_uri_mismatch`: nuevo cliente OAuth
- Branding por municipio
- Menú hamburguesa, botones sin estilo, 403.html
