# 🚗 Sistema de Estacionamiento Medido

Aplicación web en **Django 5.2** para la gestión integral del estacionamiento medido municipal.  
Soporta múltiples municipios y roles: conductor, inspector, vendedor y administrador.

---

## ✨ Funcionalidades por rol

### 👤 Conductores
- Registro y finalización de estacionamiento (descuenta saldo automáticamente)
- Saldo personal: si no alcanza, redirige a MercadoPago
- Historial de estacionamientos e infracciones
- Carga de saldo online con MercadoPago
- Exenciones: total (nunca paga), parcial (exento en ciertas subcuadras) o normal
- **Tolerancia de gracia al estacionar**: si el vehículo tiene una infracción pendiente y
  el conductor estaciona dentro del período de gracia configurado, la infracción se anula
  automáticamente. Si estaciona fuera del período, ve una notificación con los 3 timestamps
  (hora de verificación, fin de gracia, hora de estacionamiento) y puede pagar la infracción
  desde la app.

### 🕵️ Inspectores
- Verificación de vehículos por patente: pago / impago / exento / abono mensual
- Registro de infracciones con foto GPS y subcuadra
- PDF de infracciones del día (reportlab)
- Tolerancia configurable antes de multar (15 min entre infracciones)

### 🏪 Vendedores
- Registro manual de estacionamientos (cobro en efectivo, diferencia auto/moto)
- Cobro de infracciones por patente (aplica tolerancia de gracia automáticamente)
- Abono mensual por vehículo
- Carga de saldo a conductores
- Resumen de caja con comisiones y cierre de turno

### 🛠️ Administradores
- Gestión de usuarios, inspectores y vendedores
- Gestión de tarifas por municipio
- Gestión de exenciones (totales y parciales por subcuadra)
- Panel con estadísticas generales

---

## 🏗️ Arquitectura

```
views → use_cases → services → domain
```

- **Domain**: enums, políticas de saldo y vehículo, reglas de verificación
- **Use Cases**: estacionar, finalizar, pagar infracción, registrar movimiento
- **Services**: verificación (con tolerancia), infracciones, caja
- **Views**: entrada HTTP, validaciones de formulario, mensajes al usuario

### Patrones de diseño

**Factory** — `EstacionamientoFactory.crear()` centraliza la creación de estacionamientos con validaciones y estado inicial.

**Strategy** — La verificación de vehículos aplica una estrategia según tipo de conductor: exento total, exento parcial o normal.

---

## 🔐 Control de acceso

- `AbstractUser` con `correo` como campo de login (USERNAME_FIELD)
- Flags booleanos: `es_admin`, `es_inspector`, `es_vendedor`, `es_conductor`
- Decorador `@require_role(...)` en todas las vistas sensibles
- Redirección automática según rol en el inicio

---

## 🌎 Multi-municipio

Cada entidad (usuario, vehículo, subcuadra, estacionamiento, infracción) pertenece a un municipio.  
El sistema es multi-tenant básico: cada municipio opera de forma independiente.

---

## 🧪 Tests

```bash
python manage.py test app_estacionamiento
# 89 tests, OK
```

Cobertura por módulo:
- Acceso anónimo y redirecciones
- Control de roles por vista (tests_roles.py)
- Flujo completo conductor (estacionar → pagar → historial)
- Lógica de saldo, infracciones, abono, comisiones, multi-municipio, tesorero
- Tolerancia de gracia: dentro, en el límite, fuera, tolerancia=0, doble pago (tests_servicios.py)

---

## 🛠️ Tecnologías

| Capa | Tecnología |
|---|---|
| Backend | Django 5.2, Python 3.12 |
| Base de datos | SQLite (dev) / PostgreSQL (prod) |
| Autenticación | Django auth + `correo` como USERNAME_FIELD |
| Frontend | HTML + CSS (estilos propios) |
| Tests | pytest + pytest-cov |

---

## 🚀 Instalación local

```bash
git clone https://github.com/PolloLopez/estacionamiento_proyecto
cd estacionamiento_proyecto

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt

python manage.py migrate
python manage.py runscript crear_usuarios  # carga datos de prueba

python manage.py runserver
```

---

## ⚙️ Variables de entorno

Crear un archivo `.env` en la raíz (no commitear):

```env
SECRET_KEY=tu-clave-secreta
DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3

# MercadoPago (próximamente)
MP_ACCESS_TOKEN=
MP_PUBLIC_KEY=
```

---

## 📋 Estado del proyecto

### ✅ Completado

- Roles y control de acceso completo (conductor, inspector, vendedor, admin, tesorero)
- Flujos de conductor, inspector, vendedor, admin y tesorero
- Exenciones totales y parciales por subcuadra
- Caja auditada con cierre de turno y comisiones
- Multi-municipio básico (datos aislados por municipio)
- Tolerancia de gracia configurable: anula infracciones automáticamente al estacionar
- Notificación con 3 timestamps cuando se estaciona fuera de tolerancia
- Cobro de infracciones por patente (vendedor, en efectivo, con tolerancia aplicada)
- MercadoPago: carga de saldo online (webhook integrado)
- PDF de infracciones del día (reportlab)
- Google OAuth
- 89 tests pasando

### 📅 Próximamente

- API REST (Django REST Framework + JWT)
- Deploy activo (Railway Hobby cuando se reactive)
- Inspector como cobrador (paid feature)

---

## 📁 Estructura relevante

```
app_estacionamiento/
├── domain/          # Políticas puras (saldo, vehículo)
├── use_cases/       # Orquestación (estacionar, pagar infracción, cobrar)
├── services/        # Lógica de negocio por dominio (horarios, saldo, infracciones, caja)
├── services_*.py    # Shims de compatibilidad (re-exportan desde services/)
├── views.py         # Fachada pura (98 líneas, re-exporta por rol)
├── views_*.py       # Vistas por rol (conductor, inspector, vendedor, admin, tesorero, auth, mp)
├── models.py        # Modelos Django
├── decorators.py    # @require_role, @require_login
├── factories.py     # EstacionamientoFactory
└── tests*.py        # 89 tests (tests.py, tests_roles.py, tests_servicios.py)

templates/
├── admin/           # Paneles de administración
├── inspectores/     # Paneles de inspector
├── usuarios/        # Paneles de conductor
└── vendedores/      # Paneles de vendedor
```
