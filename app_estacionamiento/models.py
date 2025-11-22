from django.db import models
from django.utils import timezone
from datetime import timedelta

# 👤 Usuario del sistema (puede ser conductor, inspector, vendedor o admin)
class Usuario(models.Model):
    nombre = models.CharField(max_length=100)  # Nombre completo del usuario
    correo = models.EmailField(unique=True)    # Correo único para login/identificación
    saldo = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Saldo disponible

    # Flags de rol
    es_conductor = models.BooleanField(default=True)   # Por defecto, todo usuario es conductor
    es_inspector = models.BooleanField(default=False)  # Flag para distinguir inspectores
    es_vendedor = models.BooleanField(default=False)   # Flag para distinguir vendedores
    es_admin = models.BooleanField(default=False)      # Flag para distinguir administradores

        # Contraseña (para login simple)
    password = models.CharField(max_length=10, default="1234")

    def __str__(self):
        return self.nombre

# 🚗 Vehículo asociado a uno o varios usuarios
class Vehiculo(models.Model):
    patente = models.CharField(max_length=20, unique=True)  # Identificador único del vehículo
    usuarios = models.ManyToManyField(Usuario, related_name='vehiculos')  # Relación N:M con usuarios
    exento_en_zona = models.BooleanField(default=False)  # Si está exento en toda la zona
    subcuadras_exentas = models.ManyToManyField('Subcuadra', blank=True)  # Exenciones específicas

    def __str__(self):
        return self.patente

    def esta_exento_en(self, subcuadra):
        """
        Verifica si el vehículo está exento en una subcuadra específica.
        - Si tiene exención general, devuelve True.
        - Si no, revisa si la subcuadra está en su lista de exenciones.
        """
        if self.exento_en_zona:
            return True
        return self.subcuadras_exentas.filter(id=subcuadra.id).exists()


# 🏙️ Subcuadra representa una altura específica de una calle
class Subcuadra(models.Model):
    calle = models.CharField(max_length=100)  # Ejemplo: "Calle 21"
    altura = models.IntegerField()            # Ejemplo: 300, 350, etc.

    def __str__(self):
        return f"{self.calle}.{self.altura}"


# 💰 Tarifa por hora de estacionamiento
class Tarifa(models.Model):
    precio_por_hora = models.DecimalField(max_digits=6, decimal_places=2)  # Precio unitario

    def __str__(self):
        return f"${self.precio_por_hora}/hora"


# 🅿️ Estacionamiento en vía pública
class Estacionamiento(models.Model):
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE)  # Vehículo estacionado
    subcuadra = models.ForeignKey(Subcuadra, on_delete=models.CASCADE)  # Ubicación
    hora_inicio = models.DateTimeField(default=timezone.now)  # Inicio del estacionamiento
    hora_fin = models.DateTimeField(null=True, blank=True)    # Fin del estacionamiento
    costo = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Costo calculado
    activo = models.BooleanField(default=True)  # Flag para saber si sigue activo

    def __str__(self):
        return f"{self.vehiculo.patente} en {self.subcuadra}"

    def finalizar(self, estrategia=None):
        """
        Finaliza el estacionamiento y calcula el costo.
        - Usa una estrategia (Strategy Pattern) para calcular el costo.
        - Si no se pasa estrategia, usa EstrategiaExencion por defecto.
        - Marca el estacionamiento como inactivo y guarda el costo.
        """
        from .estrategias import EstrategiaExencion

        self.hora_fin = timezone.now()
        duracion = (self.hora_fin - self.hora_inicio).total_seconds() / 3600

        if estrategia is None:
            estrategia = EstrategiaExencion()

        self.costo = round(estrategia.calcular(self.vehiculo, self.subcuadra, duracion), 2)
        self.activo = False
        self.save()
        return self.costo


# 🚨 Infracción generada por un inspector
class Infraccion(models.Model):
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE)  # Vehículo infractor
    inspector = models.ForeignKey(Usuario, on_delete=models.CASCADE)  # Inspector que la registró
    subcuadra = models.ForeignKey(Subcuadra, on_delete=models.CASCADE)  # Ubicación
    estacionamiento = models.ForeignKey(Estacionamiento, on_delete=models.CASCADE, null=True, blank=True)  # Relación opcional
    fecha = models.DateTimeField(default=timezone.now)  # Fecha de la infracción
    cancelada = models.BooleanField(default=False)      # Si fue cancelada
    notificada = models.BooleanField(default=False)     # Si se notificó al usuario

    def __str__(self):
        return f"Infracción a {self.vehiculo.patente} por {self.inspector.nombre}"

    def verificar_cancelacion(self):
        """
        Verifica si el estacionamiento fue pagado dentro de los 15 minutos.
        - Si se finalizó y se pagó en menos de 900 segundos, se cancela.
        - Devuelve mensaje de estado.
        """
        if self.estacionamiento and self.estacionamiento.hora_fin:
            diferencia = self.estacionamiento.hora_fin - self.fecha
            if diferencia.total_seconds() <= 900:
                self.cancelada = True
                self.save()
                return "Infracción cancelada y notificada"
        return "Infracción sigue activa"


# 🔔 Notificación enviada a un usuario
class Notificacion(models.Model):
    destinatario = models.ForeignKey(Usuario, on_delete=models.CASCADE)  # Usuario que recibe la notificación
    mensaje = models.TextField()  # Texto del mensaje
    fecha = models.DateTimeField(auto_now_add=True)  # Fecha de creación
    leida = models.BooleanField(default=False)  # Flag para saber si fue leída

    def __str__(self):
        return f"Notificación para {self.destinatario.nombre}"
