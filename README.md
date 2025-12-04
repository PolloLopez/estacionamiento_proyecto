# 🚗 Sistema de Estacionamiento Medido

Aplicación web desarrollada en **Django** para la gestión del estacionamiento medido en la ciudad.  
Permite administrar distintos roles de usuario (conductor, inspector, vendedor y administrador), registrar estacionamientos, infracciones y cobros, y visualizar historiales.

---

## ✨ Funcionalidad por rol

### 👤 Conductores
- **Registro de estacionamiento:** el conductor ingresa la patente de su vehículo y selecciona la subcuadra donde estaciona.
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
El sistema utiliza el **patrón Factory** para la creación de objetos relacionados con los distintos roles de usuario (conductor, inspector, vendedor, administrador).  
De esta forma, al registrar un nuevo usuario, el sistema instancia automáticamente el tipo de rol correspondiente sin necesidad de que el desarrollador cree manualmente cada objeto.

Ejemplo conceptual:
```python
class UsuarioFactory:
    def crear_usuario(tipo, datos):
        if tipo == "conductor":
            return Conductor(**datos)
        elif tipo == "inspector":
            return Inspector(**datos)
        elif tipo == "vendedor":
            return Vendedor(**datos)
        elif tipo == "admin":
            return Administrador(**datos)
🎯 Strategy
En las funciones de verificación de vehículos por parte de los inspectores, se aplica el patrón Strategy. Cada vehículo puede tener una estrategia distinta para determinar si debe pagar o no:

Estrategia ExentoTotal: siempre devuelve "exento".

Estrategia ExentoParcial: verifica si la subcuadra está dentro de las exentas.

Estrategia Normal: calcula si el estacionamiento está pago o impago según saldo y tiempo.

Ejemplo conceptual:

python
class EstrategiaPago:
    def verificar(self, estacionamiento):
        raise NotImplementedError

class ExentoTotal(EstrategiaPago):
    def verificar(self, estacionamiento):
        return "Exento"

class ExentoParcial(EstrategiaPago):
    def verificar(self, estacionamiento):
        if estacionamiento.subcuadra in estacionamiento.conductor.subcuadras_exentas:
            return "Exento"
        return "Debe pagar"

class Normal(EstrategiaPago):
    def verificar(self, estacionamiento):
        return "Pago" if estacionamiento.pagado else "Impago"

        
Esto permite que el inspector simplemente invoque la estrategia correspondiente sin preocuparse por la lógica interna.

🛠️ Tecnologías utilizadas
Backend: Django 5.x

Frontend: HTML + CSS (estilos personalizados)

Base de datos: SQLite (por defecto, fácilmente reemplazable por PostgreSQL/MySQL)

Autenticación: Sistema de usuarios propio con roles

Scripts de prueba: crear_usuarios.py para cargar datos iniciales

Patrones de diseño: Factory y Strategy para la gestión de roles y verificación de estacionamientos

🚀 Instalación y ejecución
Clonar el repositorio:

bash
git clone https://github.com/PolloLopez/estacionamiento_proyecto
cd 