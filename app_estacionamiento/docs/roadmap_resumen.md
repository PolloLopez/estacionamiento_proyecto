app_estacionamiento/docs/roadmap_resumen.md
🧭 ROADMAP_RESUMEN — ESTADO REAL (MAYO 2026)

        🔴 FASE 1.1 — HARDENING BACKEND

👉 97% COMPLETO
⏳ Restante estimado: 6–10 hs

✅ COMPLETADO

✔ Django Auth estándar estabilizado
✔ request.user unificado
✔ Eliminación de middleware legacy
✔ Roles funcionando correctamente
✔ Routing por roles estable
✔ Decorators unificados
✔ Login por correo funcionando
✔ CSRF corregido
✔ URLs normalizadas
✔ Sistema inspectores estable
✔ Sistema vendedores estable
✔ Tests básicos funcionando
✔ Navegación corregida
✔ Exenciones integradas al flujo principal
✔ Arquitectura backend estabilizada

❗ FALTA (CRÍTICO)
🔐 Ownership real

⏳ 2–3 hs

Validar propietario real de vehículo
Verificación fuerte de relaciones
Evitar asociaciones inválidas
💣 Constraints DB

⏳ 2–4 hs

Unique constraints
Índices
Validaciones DB-level
Protección contra race conditions
💰 Validación fuerte de saldo

⏳ 1–2 hs

Atomicidad
Protección saldo negativo
Transacciones seguras


        🟡 FASE 2 — SISTEMA DE USUARIOS

👉 65% COMPLETO
⏳ Restante estimado: 10–16 hs

✅ COMPLETADO

✔ Login
✔ Registro
✔ Sesiones Django
✔ Navegación base
✔ Roles por usuario
✔ Asociación vehículo/usuario base

🔜 PENDIENTE
🔐 Google Login

⏳ 3–5 hs

👤 Perfil de usuario

⏳ 2–4 hs

Datos personales
Vehículos asociados
Historial
Estado cuenta
📧 Recuperación de contraseña

⏳ 2–3 hs

📱 Validaciones UX usuario

⏳ 3–4 hs


        📱 FASE 3 — UX/UI

👉 45% COMPLETO
⏳ Restante estimado: 12–20 hs

✅ COMPLETADO

✔ Navbar funcional
✔ Templates base
✔ Navegación por rol
✔ Paneles operativos
✔ CSS base estable

🔜 PENDIENTE
🎨 Limpieza visual final

⏳ 3–5 hs

🔒 Menús dinámicos por permisos

⏳ 2–3 hs

⚠️ Feedback visual

⏳ 2–4 hs

alerts
estados
loaders
mensajes de éxito/error
📱 Responsive/mobile

⏳ 5–8 hs

        🧪 FASE 4 — TESTING REAL

👉 25% COMPLETO
⏳ Restante estimado: 12–18 hs

✅ COMPLETADO

✔ Tests básicos auth
✔ Tests básicos estacionamiento

🔜 PENDIENTE
🚗 Flujo conductor real

⏳ 2–3 hs

👮 Flujo inspector calle

⏳ 3–5 hs

💰 Flujo vendedor

⏳ 2–3 hs

💣 Casos límite

⏳ 3–5 hs

doble estacionamiento
saldo insuficiente
race conditions
exenciones
permisos


        📊 FASE 5 — AUDITORÍA Y TRAZABILIDAD

👉 10% COMPLETO
⏳ Restante estimado: 8–14 hs

🔜 PENDIENTE
logs
historial de cambios
auditoría admin
trazabilidad multas
trazabilidad saldo
operaciones sensibles

        🚀 FASE 6 — SAAS / MULTI-MUNICIPIO

👉 15% COMPLETO
⏳ Restante estimado: 40–80 hs

✅ YA EXISTE BASE

✔ Modelo municipio
✔ Asociación usuario/municipio
✔ Asociación vehículo/municipio

🔜 FALTA
🧩 Separación modular real

⏳ 10–20 hs

🌎 Multi-tenant real

⏳ 12–20 hs

📍 Geolocalización

⏳ 8–16 hs

🔌 API REST

⏳ 8–16 hs

💳 MercadoPago

⏳ 6–12 hs

🧠 ESTADO GENERAL REAL
🔥 EL PROYECTO YA NO ES UN PROTOTIPO

Ahora tiene:

✅ arquitectura coherente
✅ auth estable
✅ roles reales
✅ navegación consistente
✅ backend sólido
✅ estructura SaaS inicial
✅ testing inicial
✅ separación lógica razonable

📌 ESTIMACIÓN GLOBAL REAL
Para MVP MUNICIPAL UTILIZABLE

⏳ 40–70 hs

(depende UX + testing real)

Para SaaS serio multi-municipio

⏳ 120–250 hs

(depende apps móviles, pagos, APIs, observabilidad, deploy, etc)