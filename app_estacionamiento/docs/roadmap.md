docs/roadmap.md
# 🚗 Sistema de Estacionamiento Medido — Roadmap del Proyecto

## 📌 Estado actual del sistema (Abril 2026)

El sistema ya cuenta con una base sólida funcional tanto a nivel backend como de interfaz básica.
Se encuentra en una etapa **pre-SaaS**, con arquitectura lista para escalar.

👉 Se completó la estabilización de navegación y sesiones.

---

## ✅ FUNCIONALIDADES IMPLEMENTADAS

### 🔐 Autenticación y roles

* Sistema de usuarios personalizado (`Usuario`)
* Roles implementados:

  * Conductor
  * Inspector
  * Vendedor
  * Administrador
* Middleware propio (`UsuarioMiddleware`)
* Decoradores de acceso (`require_login`, `require_role`)
* 🔥 Corrección completa de uso de `request.usuario` en templates

---

### 🚗 Gestión de vehículos

* Registro de vehículos por patente
* Asociación de vehículos a usuarios
* Soporte para:

  * Exento global
  * Exento por subcuadras

⚠️ Nota futura:
La patente es única global → esto deberá ajustarse para multi-municipio.

---

### 🧠 Sistema de exenciones (CORE DEL NEGOCIO)

* Lógica centralizada en modelo (`esta_exento_en`)
* Soporte completo:

  * Exención total
  * Exención parcial por subcuadra
* Integración con:

  * Verificación de inspectores
  * Registro de 

---

### 🅿️ Estacionamientos

* Inicio de estacionamiento
* Finalización con cálculo de costo
* Control de saldo
* Historial por usuario

---

### ⚠️ 

* Registro manual por inspector
* Asociación con:

  * Vehículo
  * Subcuadra
  * Estacionamiento
* Soporte de imagen (Pillow)
* Validación de exenciones antes de multar

---

### 🧑‍💼 Panel administrativo (nivel 1)

* Panel HTML funcional
* Filtros por rol
* Visualización de:

  * Estacionamientos
  *  recientes
* Carga de saldo manual
* 🔥 Navegación corregida (urls + templates)

---

### 🚧 Panel de exenciones (nivel 1 — funcional)

* Búsqueda de vehículo por patente
* Toggle de exención global
* Selección de subcuadras
* Guardado desde UI (sin código)
* Filtro de subcuadras por texto (JS básico)

👉 Funcional completamente desde interfaz.

---

### 🎨 Frontend base

* Template base (`base.html`)
* Navbar dinámica por rol
* CSS global funcionando correctamente
* Manejo correcto de archivos estáticos
* 🔥 Corrección de visibilidad de navegación por sesión

---

## ⚙️ MEJORAS TÉCNICAS REALIZADAS

* Corrección de STATIC (DEBUG vs producción)
* Eliminación de código duplicado en lógica de exenciones
* Unificación de validaciones (`esta_exento_en`)
* Corrección de imports y estructura Django
* Configuración correcta de Pillow
* Limpieza de archivos innecesarios
* 🔥 Corrección de:
  * CSRF issues
  * Login manual
  * Sesiones
  * Uso incorrecto de `request.user`

---

## 🧪 ESTADO ACTUAL: LISTO PARA TESTEO REAL

👉 El sistema ya puede ser probado en flujo completo:

* Login por roles
* Navegación por paneles
* Registro de estacionamientos
* Verificación por inspector
* Registro de 
* Gestión de exenciones

---

## 🚀 PRÓXIMOS PASOS (CORTO PLAZO)

### 🧪 TEST FUNCIONAL COMPLETO (PRIORIDAD 🔥)

* [ ] Flujo completo inspector (calle)
* [ ] Flujo conductor (saldo + estacionamiento)
* [ ] Flujo vendedor
* [ ] Validación de errores reales

---

### 🔥 Panel de exenciones — Nivel PRO

* [ ] Autocomplete de patentes (AJAX)
* [ ] Selección dinámica sin recarga
* [ ] Mejora de UX (feedback visual)
* [ ] Carga automática del vehículo
* [ ] Guardado sin reload (AJAX)

---

### ⚠️ Lógica crítica faltante

* [ ] Tolerancia de tiempo para inspectores
* [ ] Estados de infracción (impaga / pagada)
* [ ] Control estricto de saldo negativo
* [ ] Validaciones adicionales de seguridad

---

### 📊 Auditoría y control

* [ ] Registro de acciones (logs)
* [ ] Historial de cambios en exenciones
* [ ] Trazabilidad de operaciones

---

## 🧱 PRÓXIMA ETAPA (MEDIANO PLAZO)

### 🧩 Arquitectura SaaS

* Separación por apps:

  * accounts
  * municipios
  * estacionamientos
  * pagos
  * multas
* 🔥 Multi-municipio (multi-tenant) — PRIORIDAD ALTA
* Validación de ubicación del vehículo (subcuadra) en inspecciones
* Geolocalización de inspector (GPS)
* Detección automática de subcuadra
* Validación en tiempo real contra exenciones

---

### 🔌 API REST

* Implementación con Django REST Framework
* Autenticación JWT
* Endpoints:

  * Login
  * Estacionamientos
  * Vehículos
  * 
  * Pagos

---

### 💳 Pagos

* Integración MercadoPago
* Webhooks
* Recarga de saldo automática

---

### 💻 Frontend moderno

* Migración a React / Next.js
* Apps separadas:

  * Usuario
  * Inspector
  * Admin

---

## 🏁 OBJETIVO FINAL

Construir una plataforma SaaS para municipios que permita:

* Gestión completa del estacionamiento medido
* Control en tiempo real por inspectores
* Cobro digital integrado
* Administración centralizada
* Escalabilidad multi-ciudad

---

## 🧠 NOTA DEL PROYECTO

El sistema ya dejó de ser un prototipo.

👉 Ahora entra en fase de:

**VALIDACIÓN REAL + ENDURECIMIENTO DEL BACKEND**

---

## 📌 SIGUIENTE HITO

👉 🧪 TEST REAL DEL SISTEMA (flujo completo)

ANTES de:

👉 Panel de exenciones PRO

---
