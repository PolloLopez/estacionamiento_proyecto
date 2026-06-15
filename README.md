# 🚗 Sistema de Estacionamiento Medido

Aplicación web en **Django 5.2** para la gestión integral del estacionamiento medido municipal.  
Soporta múltiples municipios y roles: conductor, inspector, vendedor y administrador.

---

## ✨ Funcionalidades por rol

### 👤 Conductores
- Registro y finalización de estacionamiento (descuenta saldo automáticamente)
- Saldo personal: si no alcanza, queda como impago
- Historial de estacionamientos e infracciones
- Carga de saldo (en efectivo vía vendedor; MercadoPago en desarrollo)
- Exenciones: total (nunca paga), parcial (exento en ciertas subcuadras) o normal

### 🕵️ Inspectores
- Verificación de vehículos por patente: pago / impago / exento
- Registro de infracciones con foto y subcuadra
- Registro manual de cobros
- Caja auditada: movimientos, cierre de turno con confirmación
- Tolerancia configurable antes de multar

### 🏪 Vendedores
- Registro manual de estacionamientos (cobro en efectivo)
- Carga de saldo a conductores
- Resumen de caja de la jornada

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
# 45 tests, OK

pytest
# Con cobertura: pytest --cov=app_estacionamiento --cov-report=term-missing
```

Cobertura por módulo:
- Acceso anónimo y redirecciones
- Control de roles por vista
- Flujo completo conductor (estacionar → pagar → historial)
- Lógica de saldo (deducción, saldo insuficiente, duplicados ACTIVO)

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

### ✅ Completado (v1.0-audit-completa)

- Roles y control de acceso completo
- Flujos de conductor, inspector, vendedor y admin
- Exenciones totales y parciales
- Caja auditada con cierre de turno
- Multi-municipio básico
- Constraint de unicidad en DB (un ACTIVO por vehículo)
- Use Cases desacoplados
- 45 tests pasando

### 🔜 En progreso

- **MercadoPago**: carga de saldo online y pago de infracciones
- **Deploy**: Railway (PostgreSQL + HTTPS + dominio público)
- **Settings de producción**: SECRET_KEY segura, DEBUG=False, WhiteNoise

### 📅 Próximamente

- API REST (Django REST Framework + JWT)
- Frontend moderno (React / Next.js)
- SaaS multi-municipio completo con facturación

---

## 📁 Estructura relevante

```
app_estacionamiento/
├── domain/          # Reglas de negocio puras
├── use_cases/       # Casos de uso (orquestación)
├── services_*.py    # Servicios por dominio
├── models.py        # Modelos Django
├── views.py         # Vistas HTTP
├── decorators.py    # @require_role, @require_login
├── factories.py     # EstacionamientoFactory
└── tests*.py        # Tests unitarios e integración

templates/
├── admin/           # Paneles de administración
├── inspectores/     # Paneles de inspector
├── usuarios/        # Paneles de conductor
└── vendedores/      # Paneles de vendedor
```
