🚀 Roadmap_resumen — Visión del Producto

🔴 Pendientes críticos (producción)

Tolerancia de tiempo en inspecciones (gracia configurable ⏱️)
Control de saldo negativo robusto 💳
Estados de infracción completos:
pendiente
pagada
anulada
Auditoría de acciones (logs por usuario) 📋
Validaciones de seguridad:
evitar doble infracción
validar municipio en todas las operaciones
sanitización de inputs

🟡 Evolución del sistema (SaaS)

Multi-municipio completo 🔥 (YA INICIADO)
aislamiento por municipio ✔
datos independientes ✔
API REST (Django REST Framework)
Autenticación JWT
Frontend moderno (React / Next.js)

💳 Integraciones

MercadoPago (checkout + QR)
Webhooks de pago (confirmación automática)
Carga de saldo:
tarjeta 💳
puntos físicos 🏪

📱 Experiencia de usuario (clave producto)

Acceso por QR en vía pública 📍
Login rápido:
Google 🔥 (PRIORIDAD FASE 2)
Flujo sin fricción:
ingresar patente → estacionar → listo

🧠 Lógica de negocio (ACTUALIZADA)

Vehículos dinámicos 🚗 ✔
cualquier patente puede operar
no requiere registro previo
Asociación opcional usuario ↔ vehículo (fase 2)
Inspector:
valida estado
genera infracción si corresponde

🎯 Objetivo

Convertir el sistema en una plataforma SaaS municipal escalable para:

Estacionamiento medido
Control de infracciones
Recaudación digital
📌 Estado reciente (7 - Abril 2026)

✅ Fase 1 — CORE OPERATIVO (COMPLETA)
✔ Estacionar
✔ Verificar estado
✔ Infraccionar
✔ Vehículo dinámico
✔ Filtro por municipio funcionando
✔ Inspector operativo real
✔ Finalizar estacionamiento


🚀 Fase 2 — IDENTIDAD Y USUARIOS (8/4)

Login con Google 🔥
Asociación usuario ↔ patente
Historial por usuario
Base de usuarios real (ciudadanos + turistas)

💰 Fase 3 — PAGOS
MercadoPago
Saldo virtual
Webhooks
Validación automática de pago

🛰️ Fase 4 — INTELIGENCIA EN CALLE
GPS inspector
Validación automática de subcuadra
Eliminación de selección manual
Auditoría geográfica



📌 Estado del sistema (10 Abril 2026)
✅ CORE OPERATIVO FUNCIONAL

El sistema ya permite operar de punta a punta:

🚗 Estacionamiento
Crear estacionamiento desde usuario
Asociación automática vehículo ↔ usuario
Validación de patente (normalizada a mayúsculas)
Control de un solo estacionamiento activo por usuario
Prevención de duplicados
⏱️ Gestión de estado
Visualización de estacionamiento activo
Cálculo automático de duración
Estimación y cálculo real de costo
💰 Finalización
Finalización manual desde panel
Cálculo de costo por tiempo
Descuento automático de saldo
Persistencia correcta del estado (activo=False)
🚨 Inspección
Verificación de vehículos
Registro de infracciones
Validación de estacionamiento activo
🔧 Fixes importantes realizados
Corrección crítica: estacionamientos se desactivaban al crearse
Eliminación de duplicados por patentes (unique constraint)
Estandarización de patentes (uppercase)
Corrección de templates duplicados (panel.html vs inicio_usuarios.html)
Manejo seguro de inputs (None.strip() fix)
Consistencia entre backend y frontend
🧠 Decisiones de arquitectura
1 estacionamiento activo por usuario
Vehículos dinámicos (no requieren registro previo)
Factory para creación centralizada de estacionamientos
Separación clara de roles (conductor / inspector / vendedor / admin)
🚀 Estado del roadmap
✅ Fase 1 — CORE (COMPLETA)
Estacionar ✔
Verificar ✔
Infraccionar ✔
Finalizar ✔
Multi-municipio ✔
🔜 Fase 2 — IDENTIDAD (SIGUIENTE)
Login con Google
Asociación usuario ↔ vehículos
Historial por usuario
Base de ciudadanos