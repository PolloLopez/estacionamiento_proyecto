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

## 🔜 v1.1 — Producción y deploy (EN PROGRESO)

### Settings de producción
- [ ] Separar `settings_dev.py` / `settings_prod.py`
- [ ] `SECRET_KEY` desde variable de entorno
- [ ] `DEBUG=False` en producción
- [ ] `ALLOWED_HOSTS` con dominio real
- [ ] `AUTH_PASSWORD_VALIDATORS` activados
- [ ] `WhiteNoise` para archivos estáticos

### Base de datos
- [ ] `psycopg2-binary` en requirements
- [ ] `DATABASE_URL` desde variable de entorno
- [ ] PostgreSQL en Railway

### Deploy
- [ ] Deploy en Railway (PostgreSQL incluido, HTTPS automático)
- [ ] Variables de entorno configuradas en Railway
- [ ] `collectstatic` verificado
- [ ] Sistema público accesible

---

## 🔜 v1.2 — MercadoPago

### Carga de saldo
- [ ] Instalar SDK `mercadopago`
- [ ] Vista `iniciar_carga_saldo`: crea preferencia de pago en MP
- [ ] Redireccionamiento a checkout MP
- [ ] Webhook `mp_webhook`: verifica pago y acredita saldo
- [ ] Vista `pago_exitoso` / `pago_fallido` / `pago_pendiente`
- [ ] Registro en `MovimientoCaja` al acreditar
- [ ] Sandbox con tarjetas de prueba

### Pago de infracciones
- [ ] Flow similar: preferencia MP → webhook → llama `pagar_infraccion_uc`
- [ ] Actualización de estado `Infraccion.estado = "pagada"`

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
