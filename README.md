# 🚗 Sistema de Estacionamiento Medido

Aplicación web desarrollada en **Django** para la gestión del estacionamiento medido en la ciudad.  
Permite administrar distintos roles de usuario (conductor, inspector, vendedor y administrador), registrar estacionamientos, infracciones y cobros, y visualizar historiales.

---

## ✨ Funcionalidad por rol

### 👤 Conductores
- **Registro de estacionamiento:** el conductor ingresa la patente de su vehículo y estaciona.
- **Finalización de estacionamiento:** al terminar, puede finalizar el estacionamiento. El sistema calcula el costo según la duración y descuenta del saldo.
- **Saldo:** cada conductor tiene una cuenta con saldo. Si no alcanza, no puede finalizar el estacionamiento y queda como impago.
- **Historial:** puede consultar todos sus estacionamientos pasados y ver si están pagos o impagos.
- **Infracciones:** puede ver las infracciones registradas sobre sus vehículos.
- **Exenciones:**
  - **Exento total:** nunca paga estacionamiento en ninguna subcuadra.
  - **Exento parcial:** no paga en ciertas calles/subcuadras específicas, pero sí en el resto.
  - **Normal:** debe pagar siempre.

---

### 🕵️ Inspectores
- **Panel de control:** acceso a todas las funciones desde un menú central.
- **Verificación de vehículos:** ingresan una patente y el sistema indica si está pago, impago o exento.  
  👉 Aquí se aplica el **patrón Strategy**, ya que la verificación se realiza según la estrategia de cálculo correspondiente al tipo de conductor (exento total, exento parcial o normal).
- **Registro de infracciones:** pueden generar un acta de infracción, adjuntando foto y seleccionando la subcuadra.
- **Registro manual de cobros:** en caso de cobros especiales, pueden registrarlos manualmente.
- **Resumen rápido:** visualizan estacionamientos no pagados e infracciones recientes para tener control en la calle.

---

### 🏪 Vendedores
- **Registro manual de estacionamientos:** permiten a conductores pagar en efectivo y registrar el estacionamiento en el sistema.
- **Resumen de caja:** visualizan los cobros realizados y el balance de su jornada.

---

### 🛠️ Administradores
- **Panel administrativo:** acceso al panel de Django para gestionar usuarios, vehículos, subcuadras e infracciones.
- **Estadísticas:** pueden ver estacionamientos recientes, infracciones registradas y distinguir entre conductores exentos totales, parciales y normales.
- **Gestión de roles:** asignan permisos y roles a cada usuario.

---

## 🧩 Uso de patrones de diseño

### 🏭 Factory

El sistema utiliza el patrón Factory para la creación de estacionamientos.

Esto permite centralizar la lógica de creación, validaciones y asignación de valores
como duración, costo inicial y usuario que registra.

Ejemplo conceptual:

```python
class EstacionamientoFactory:
    @staticmethod
    def crear(vehiculo, subcuadra, duracion, registrado_por=None):
        inicio = timezone.now()
        fin = inicio + timedelta(hours=float(duracion))

        estacionamiento = Estacionamiento.objects.create(
            vehiculo=vehiculo,
            subcuadra=subcuadra,
            hora_inicio=inicio,
            hora_fin=fin,
            registrado_por=registrado_por,
            activo=True
        )

        return estacionamiento

🎯 Strategy
En las funciones de verificación de vehículos por parte de los inspectores, se aplica el patrón Strategy. Cada vehículo puede tener una estrategia distinta para determinar si debe pagar o no:

Estrategia ExentoTotal: siempre devuelve "exento".

Estrategia ExentoParcial: verifica si la subcuadra está dentro de las exentas.

Estrategia Normal: calcula si el estacionamiento está pago o impago según saldo y tiempo.

👉 Nota: actualmente la lógica se encuentra parcialmente implementada en vistas,
pero se proyecta migrarla completamente a un sistema de estrategias desacopladas.

        
Esto permite que el inspector simplemente invoque la estrategia correspondiente sin preocuparse por la lógica interna.

## 🌎 Soporte multi-municipio

El sistema permite operar múltiples municipios de forma independiente.

Cada entidad clave está asociada a un municipio:
- Usuarios
- Subcuadras
- Estacionamientos
- Infracciones

Esto permite escalar la solución como plataforma SaaS para distintas ciudades.

🛠️ Tecnologías utilizadas
Backend: Django 5.x

Frontend: HTML + CSS (estilos personalizados)

Base de datos: SQLite (por defecto, fácilmente reemplazable por PostgreSQL/MySQL)

Autenticación: Sistema de usuarios propio con roles
## 🔐 Autenticación

Actualmente el sistema utiliza un esquema de autenticación basado en sesión
personalizada (`request.session["usuario_id"]`).

Se encuentra planificada la migración al sistema estándar de Django (`request.usuario`)
y posteriormente a JWT para API REST.


Scripts de prueba: crear_usuarios.py para cargar datos iniciales

Patrones de diseño: Factory y Strategy para la gestión de roles y verificación de estacionamientos

🚀 Instalación y ejecución
Clonar el repositorio:

bash
git clone https://github.com/PolloLopez/estacionamiento_proyecto
cd 

## 🚧 Estado del proyecto

El sistema se encuentra en fase avanzada de desarrollo.

✔ Funcionalidades principales implementadas  
✔ Roles operativos  
✔ Gestión de exenciones completa  
✔ Paneles funcionales  

🔜 Próximos pasos:
- Interfaz administrativa avanzada (exenciones desde UI)
- API REST
- Integración con pagos (MercadoPago)
- Frontend moderno (React / Next.js)