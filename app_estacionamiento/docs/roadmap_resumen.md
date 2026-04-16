🧭 ROADMAP ACTUALIZADO (15 ABRIL 2026) 
Te lo rearmo con lo que definiste hoy (modelo A + ownership de vehículo controlado)

🔴 FASE 1.1 — HARDENING PRODUCTIVO (CRÍTICO)

👉 Se mantiene, pero le agrego lo que descubriste hoy

Incluye
⏱️ Tolerancia configurable de tiempo
💳 Control de saldo negativo robusto
🚫 Evitar doble infracción
🏛️ Validación de municipio en TODAS las operaciones
🧼 Sanitización de inputs
📋 Auditoría completa
📄 Estados de infracción (pendiente / pagada / anulada)
🔥 NUEVO (clave por lo que vimos hoy)
🔐 Validación de ownership en acciones críticas:
finalizar estacionamiento
ver historial
🚗 Normalización de acceso a vehículo:
evitar acceso cruzado entre usuarios
🧱 Protección contra manipulación por ID (IDOR)

⏱️ Nueva estimación:
👉 22 – 32 horas

🟡 FASE 2 — IDENTIDAD Y VEHÍCULOS (REDEFINIDA)

👉 Esta fase cambia FUERTE respecto a tu versión anterior

🎯 OBJETIVO

Pasar de:

“vehículo suelto”

a:

“vehículo con ownership controlado dentro del sistema”

Incluye
🔐 Identidad
Login (ya ✔)
Preparar OAuth (opcional)
🚗 Ownership de vehículos (NUEVO CORE)
Relación:
Usuario ↔ Vehiculo (ManyToMany)
🔒 Reglas de ownership
✔ El usuario puede operar SOLO sus vehículos
✔ El creador del estacionamiento mantiene control (modelo A)
✔ Se registra SIEMPRE quién hizo la acción
⚠️ Conflictos de patente
Detección:
“este vehículo ya está asociado a otro usuario”

Opciones:

warning
permitir con log
futura validación OTP
📜 Historial correcto
por usuario
por vehículo
por acción
📊 Auditoría extendida

Ejemplo:

Vehículo: ABC123
Creado por: vendedor@test.com
Finalizado por: conductor@test.com

⏱️ Estimación realista:
👉 20 – 30 horas

💰 FASE 3 — PAGOS (CORE DE NEGOCIO)

👉 Se mantiene igual (bien definida)

Pero ahora:

🔥 Impacta con vehículos
saldo ligado a usuario
consumo ligado a estacionamiento
consistencia entre:
usuario
vehículo
transacción

⏱️ 24 – 36 horas

🔥 FASE 4 — MULTI-MUNICIPIO (SaaS REAL)

👉 Acá entra algo importante nuevo

🔐 Aislamiento + ownership
Un vehículo NO puede cruzar municipios
Usuario pertenece a municipio
Todas las validaciones usan:
vehiculo__municipio = usuario.municipio
🔥 Nuevo riesgo que evitás
fuga de datos entre municipios
multas mal asignadas

⏱️ 14 – 20 horas

📱 FASE 5 — EXPERIENCIA DE USUARIO

👉 Ahora con impacto directo del ownership

Incluye
Flujo simple:
seleccionar vehículo (auto-guardado)
“Mis vehículos”
advertencias de conflicto
UX inspector rápida

⏱️ 18 – 26 horas

🛰️ FASE 6 — INTELIGENCIA EN CALLE

👉 Se mantiene igual

Pero mejora:

validación cruzada:
vehículo
ubicación
inspector

⏱️ 20 – 30 horas

🧮 RESUMEN ACTUALIZADO
Fase	Horas
🔴 Hardening	22 – 32 h
🟡 Identidad + Vehículos	20 – 30 h
💰 Pagos	24 – 36 h
🔥 Multi-municipio	14 – 20 h
📱 UX	18 – 26 h
🛰️ Inteligencia	20 – 30 h
🧠 TOTAL NUEVO

👉 118 a 174 horas

(Sí, subió un poco — pero ahora es sistema serio)