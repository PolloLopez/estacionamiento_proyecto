docs/roadmap.md
# 🚗 Sistema de Estacionamiento Medido — Roadmap del Proyecto

## 📌 Estado actual del sistema (Abril 2026)

El sistema ya cuenta con una base sólida funcional tanto a nivel backend como de interfaz básica.
Se encuentra en una etapa **pre-SaaS**, con arquitectura lista para escalar.

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

---

### 🚗 Gestión de vehículos

* Registro de vehículos por patente
* Asociación de vehículos a usuarios
* Soporte para:

  * Exento global
  * Exento por subcuadras

---

### 🧠 Sistema de exenciones (CORE DEL NEGOCIO)

* Lógica centralizada en modelo (`esta_exento_en`)
* Soporte completo:

  * Exención total
  * Exención parcial por subcuadra
* Integración con:

  * Verificación de inspectores
  * Registro de infracciones

---

### 🅿️ Estacionamientos

* Inicio de estacionamiento
* Finalización con cálculo de costo
* Control de saldo
* Historial por usuario

---

### ⚠️ Infracciones

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
  * Infracciones recientes
* Carga de saldo manual

---

### 🚧 Panel de exenciones (nivel 1 — funcional)

* Búsqueda de vehículo por patente
* Toggle de exención global
* Selección de subcuadras
* Guardado desde UI (sin código)
* Filtro de subcuadras por texto (JS básico)

👉 Esto elimina la necesidad de modificar código para asignar exenciones.

---

### 🎨 Frontend base

* Template base (`base.html`)
* Navbar dinámica por rol
* CSS global funcionando correctamente
* Manejo correcto de archivos estáticos

---

## ⚙️ MEJORAS TÉCNICAS REALIZADAS

* Corrección de STATIC (DEBUG vs producción)
* Eliminación de código duplicado en lógica de exenciones
* Unificación de validaciones (`esta_exento_en`)
* Corrección de imports y estructura Django
* Configuración correcta de Pillow
* Limpieza de archivos innecesarios

---

## 🚀 PRÓXIMOS PASOS (CORTO PLAZO)

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
* Multi-municipio (multi-tenant)

---

### 🔌 API REST

* Implementación con Django REST Framework
* Autenticación JWT
* Endpoints:

  * Login
  * Estacionamientos
  * Vehículos
  * Infracciones
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
Actualmente se encuentra en una etapa donde:

👉 El foco debe pasar de **funcionalidad técnica**
👉 a **experiencia de usuario + escalabilidad**

---

## 📌 SIGUIENTE HITO

👉 Panel de exenciones PRO (autocomplete + UX avanzada)

Este paso transforma el sistema de:

* herramienta técnica
  ➡️ a producto usable por personal municipal

---
