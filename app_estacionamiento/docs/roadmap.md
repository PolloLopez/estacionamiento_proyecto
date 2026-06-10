# Roadmap — Sistema de Estacionamiento Medido

---

## ✅ v0.8 — Flujo real de usuarios

- Services de verificación e infracciones desacoplados
- Migración completa a `request.user`
- Caja auditada con movimientos y cierre
- Multi-municipio básico
- 17 tests pasando
- Refactor de navegación y rutas
- Use Case `finalizar_estacionamiento`
- Corrección ownership usuario ↔ vehículo
- Modelo `Infraccion` simplificado (pendiente / pagada / anulada)
- Pago de infracciones integrado a `MovimientoCaja`
- Cobro por inspector, vendedor y admin

---

## ✅ v1.0 — Auditoría completa del sistema

- **9 bugs críticos corregidos** (Meta indentation, Q condition, campo fecha, indentación services, etc.)
- Seguridad: `@require_role` en todas las vistas sensibles, validación de municipio en exenciones
- Constraint de unicidad en DB: `UniqueConstraint` con `Q(estado="ACTIVO")` para evitar duplicados
- `Tarifa` conectada al cálculo real de costo (era hardcoded)
- `finalizar_estacionamiento`: GET con confirmación + POST ejecuta Use Case
- `cerrar_caja`: GET con resumen de movimientos + POST confirma cierre
- Mensajes Django (`messages.success/warning/error`) en lugar de strings sueltos
- Corrección de todos los templates (`m.fecha` → `m.creado_en`, `duracion_real` → `duracion_horas`, etc.)
- Gestión admin: inspectores, vendedores, usuarios, tarifas, exenciones
- **45 tests pasando** (roles, acceso anónimo, flujo completo conductor)

---

## ✅ v1.1 — Producción y deploy

### Settings de producción
- [x] `SECRET_KEY` desde variable de entorno
- [x] `DEBUG=False` en producción
- [x] `ALLOWED_HOSTS` con dominio real (`estacionamiento.up.railway.app`)
- [x] `WhiteNoise` para archivos estáticos
- [x] `SITE_ID` configurable desde variable de entorno (`int(os.environ.get("SITE_ID", 2))`)

### Base de datos
- [x] `psycopg2-binary` en requirements
- [x] `DATABASE_URL` desde variable de entorno
- [x] PostgreSQL en Railway

### Deploy
- [x] Deploy en Railway (PostgreSQL, HTTPS automático)
- [x] Variables de entorno configuradas en Railway
- [x] `collectstatic` verificado
- [x] Sistema público accesible en `https://estacionamiento.up.railway.app`
- [x] Railway reconectado tras migración de repo GitHub

### Autenticación
- [x] Google OAuth configurado (cliente OAuth nuevo, URI autorizada, Social App en admin)
- [x] `SITE_ID` corregido para allauth

---

## ✅ v1.2 — UX y estabilidad

### Correcciones críticas
- [x] Backdrop hamburguesa bloqueaba links → `pointer-events:none` + document listener
- [x] Botón "Pagar y finalizar" invisible → `class="btn"` corregido
- [x] "No autorizado" sin estilo → template `403.html` con navbar
- [x] `NoReverseMatch caja_inspector` → corregido a `inspectores_caja`
- [x] Campos incorrectos en `resumen_cobros` / `resumen_infracciones`
- [x] Historial estacionamientos desbordaba en mobile → `overflow-x:auto`

### Branding por municipio
- [x] Modelo `Municipio` con `logo`, `color_primario`, `color_secundario`, `nombre_sistema`
- [x] Context processor inyecta branding en todos los templates
- [x] CSS variables sobreescribibles por municipio desde `base.html`

### MercadoPago
- [x] SDK integrado, flujo completo conductor → MP checkout → webhook → acreditación
- [x] Error 400 `invalid_auto_return` corregido (campo eliminado)
- [x] Logging detallado de errores MP
- [ ] Pasar de sandbox a producción (pendiente credenciales productivas)

---

## 🔜 v1.3 — Completar funcionalidades pendientes

- [ ] Usuarios Google OAuth: asignar `es_conductor=True` automáticamente
- [ ] Timer en inicio conductor: fix NaN:NaN (parsing de fecha JS)
- [ ] Inspector: subcuadras en formulario de infracción
- [ ] Vendedor: cobrar infracciones por patente
- [ ] Vendedor: selector de período al cerrar caja
- [ ] Modo alto contraste / uso en exterior

---

## 📅 v2.0 — API REST

- Django REST Framework
- JWT (SimpleJWT)
- Serializers por modelo
- ViewSets con permisos por rol
- Swagger / OpenAPI

---

## 📅 v3.0 — Frontend moderno

- React + Next.js
- Dashboard en tiempo real
- Mapa de subcuadras
- App mobile (React Native)

---

## 📅 v4.0 — SaaS Multi-Municipio completo

- Tenancy completa
- Facturación por municipio
- Panel municipal propio
- Reportes y métricas operativas
- Backups automáticos

---

## 🎯 Objetivo final

SaaS multi-municipio para gestión integral del estacionamiento medido, operable desde cualquier municipio de Argentina.
