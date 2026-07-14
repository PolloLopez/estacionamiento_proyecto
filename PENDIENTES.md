# Pendiente — Estacionamiento Proyecto

Última actualización: 2026-07-14

---

## 🟡 Media prioridad

### 5. Configurar email en Railway (recuperación de contraseña)
En local los emails aparecen en la consola (backend `console`). En Railway hay que setear 3 variables:
```
EMAIL_HOST_USER=tumail@gmail.com
EMAIL_HOST_PASSWORD=xxxx xxxx xxxx xxxx   ← contraseña de app de Google (no la contraseña normal)
DEFAULT_FROM_EMAIL=Sistema Estacionamiento <tumail@gmail.com>
```
La contraseña de app se genera en: Google Account → Seguridad → Verificación en dos pasos → Contraseñas de aplicaciones.
**Disparador**: cuando se reactive el deploy en Railway.

### 6. Prueba de navegador — modal tolerancia ⏸️ pendiente hasta nuevo deploy
Testear manualmente el modal diferenciado en `mis_infracciones`.
Ver pasos en `testeo.md` → sección "Test manual — Tolerancia de gracia" (Casos A, B, C, D).
**Bloqueado por**: Railway trial expirado. Hacer cuando se reactive o migre el deploy.

### 7. Tests faltantes (coverage incompleto)
- Flujo MP webhook (integración)

---

## 🟢 Baja prioridad / Futuras versiones

### 8. Evaluar migración a Digital Ocean
Railway conveniente pero con limitaciones de costo/control a largo plazo.
**Disparador**: cuando el sistema tenga usuarios reales pagando.

### 9. Inspector: foto con watermark y GPS (v2)
`Infraccion` ya tiene campo `foto` (ImageField). La marca de agua GPS ya está implementada
en `services/infracciones.py::_agregar_marca_de_agua_gps`. Falta integrar en el flujo mobile.

### 10. Inspector como cobrador (paid feature)
Agregar rol "inspector" al decorator de `registrar_estacionamiento_vendedor` y `cobrar_abono`.

### 11. Mejoras OAuth y UI
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

### Tolerancia al estacionar — integración completa ✅
- `services/infracciones.py` → nueva `calcular_estado_tolerancia()` con `MARGEN_TOLERANCIA_SEGUNDOS = 60`
  (evita cobrar por diferencias de pocos segundos). Centraliza la lógica usada en 3 lugares.
- `use_cases/estacionar_vehiculo.py` → antes de crear el Estacionamiento, busca infracción
  pendiente del vehículo: dentro de tolerancia → anula; fuera → deja pendiente + retorna timestamps.
- `views_conductor.py` → guarda timestamps en `request.session`, `inicio_usuarios` los muestra
  como card con los 3 timestamps y link a "Mis infracciones".
- `views_vendedor.py` → mismo chequeo en `registrar_estacionamiento_vendedor` (avisa por messages).
- `cobrar_infraccion_vendedor` → reemplazó lógica inline por `calcular_estado_tolerancia`.
- `use_cases/pagar_infraccion.py` → también usa `calcular_estado_tolerancia` (refactor).

### feat: aviso fuera de término al pagar infracción ✅
`mis_infracciones` calcula `ids_dentro_tolerancia` al renderizar.
Modal diferenciado: dentro de gracia → "Anular sin costo" (verde); fuera → aviso amarillo + botón rojo "Pagar $X".
El use case `pagar_infraccion_uc` decide en el servidor si anula o cobra.

### Tests tolerancia de gracia (6 tests en TestToleranciaMulta) ✅
Cubre: dentro, exactamente en el límite, fuera, tolerancia=0, doble pago.
Técnica: `Infraccion.objects.update(creado_en=...)` + `patch("...pagar_infraccion.timezone")`.

### views.py — limpieza de imports legacy ✅
157 → 98 líneas. Eliminados: models, utils, factories, services_*, use_cases, decorators, forms, django internals. Puro facade.

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

### Abono mensual — conductor paga con saldo + admin sin comisión ✅
- `AbonoMensual.MEDIOS_PAGO` ahora incluye `'saldo'` + migración 0039.
- Nueva view `pagar_abono_conductor` (GET: selección vehículo/mes, POST confirmar/cobrar con `select_for_update`).
- Admin cobra abono a través de `cobrar_abono` con `comision_monto = Decimal("0")` → 100% a tesorería.
- Conductor accede desde panel de inicio (botón "📅 Pagar abono" siempre visible).
- Panel admin: nuevo botón "📅 Abonos" en cabecera → `cobrar_abono`.

### Infracciones — conductor las paga desde la app ✅
- `mis_infracciones` muestra modal diferenciado: dentro de tolerancia → botón "Anular sin costo";
  fuera → aviso amarillo + "Pagar $X".
- `pagar_infraccion` use case decide en servidor si anula (gracia) o cobra (descuenta saldo).
- Al estacionar: infracción pendiente detectada → dentro de gracia → anula + mensaje verde;
  fuera de gracia → estacionamiento igual + notificación con 3 timestamps + link a Mis infracciones.

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
