🧭 ROADMAP ACTUALIZADO (ABRIL 2026)
🔴 FASE 1.1 — HARDENING PRODUCTIVO (CRÍTICO)

👉 Esto es lo que te falta para decir: “esto ya se puede usar en producción posta”

Incluye
⏱️ Tolerancia configurable de tiempo (gracia inspecciones)
💳 Control de saldo negativo robusto (bloqueos + edge cases)
🚫 Evitar doble infracción (constraint + lógica)
🏛️ Validación de municipio en TODAS las operaciones (clave SaaS)
🧼 Sanitización de inputs (backend + API)
📋 Auditoría completa (logs por usuario + acciones críticas)
📄 Estados de infracción:
pendiente
pagada
anulada
💡 Nota importante

Esto no es “feature”, es blindaje del sistema.
Si lo salteás → en producción se rompe.

⏱️ Estimación

18 a 28 horas

🟡 FASE 2 — IDENTIDAD Y USUARIOS

👉 Acá convertís el sistema en producto usable por personas reales

Incluye
🔐 Login con Google (OAuth)
👤 Modelo de usuario extendido
🚗 Asociación usuario ↔ vehículo (opcional)
📜 Historial por usuario
🧾 Relación usuario ↔ transacciones
⚠️ Complejidad real

No es difícil, pero:

cambia modelo mental (de “vehículo suelto” → “usuario”)
impacta en TODO
⏱️ Estimación

16 a 24 horas

💰 FASE 3 — PAGOS (CORE DE NEGOCIO)

👉 Acá aparece la plata real

Incluye
💳 Integración con MercadoPago:
Checkout
QR
🔔 Webhooks (confirmación automática)
💰 Sistema de saldo virtual
🏪 Carga manual (puntos físicos)
⚠️ Donde se complica
Webhooks bien hechos (idempotencia)
conciliación de pagos
estados intermedios
⏱️ Estimación

24 a 36 horas

🔥 FASE 4 — MULTI-MUNICIPIO COMPLETO (SaaS REAL)

👉 Ya lo empezaste, pero falta cerrarlo bien

Incluye
🏛️ Aislamiento total por municipio (DB lógico)
🔑 permisos por municipio
⚙️ configuración independiente (tarifas, reglas, tolerancias)
📊 métricas por municipio
💡 Esto te convierte en SaaS vendible
⏱️ Estimación

12 a 18 horas
(porque ya tenés base hecha)

📱 FASE 5 — EXPERIENCIA DE USUARIO (PRODUCTO)

👉 Esto define si la gente lo usa o lo abandona

Incluye
📍 Acceso por QR en calle
⚡ Flujo ultra rápido:
patente → estacionar → listo
🔐 Login rápido (Google ya integrado)
UI usable desde celular (clave inspectores)
⏱️ Estimación

16 a 24 horas

🛰️ FASE 6 — INTELIGENCIA EN CALLE (DIFERENCIAL)

👉 Esto te separa de cualquier sistema municipal básico

Incluye
📡 GPS inspector
📍 detección automática de subcuadra
🚫 eliminar selección manual
🗺️ validación geográfica de infracciones
📋 auditoría con ubicación
⚠️ Complejidad

Acá ya hay lógica + frontend + precisión GPS

⏱️ Estimación

20 a 30 horas

📊 RESUMEN TOTAL
Fase	Horas
🔴 Hardening	18 – 28 h
🟡 Usuarios	16 – 24 h
💰 Pagos	24 – 36 h
🔥 Multi-municipio	12 – 18 h
📱 UX	16 – 24 h
🛰️ Inteligencia	20 – 30 h
🧮 TOTAL ESTIMADO

👉 106 a 160 horas