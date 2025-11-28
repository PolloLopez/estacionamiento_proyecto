# app_estacionamiento/models.py
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

# 👤 Usuario del sistema (con roles y saldo)
class UsuarioManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("El correo es obligatorio")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("es_admin", True)

        return self.create_user(email, password, **extra_fields)


class Usuario(AbstractUser):
    username = None
    email = models.EmailField(unique=True)

    saldo = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    es_conductor = models.BooleanField(default=True)
    es_inspector = models.BooleanField(default=False)
    es_vendedor = models.BooleanField(default=False)
    es_admin = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UsuarioManager()   

    def __str__(self):
        return self.email
    
# 🚗 Vehículo asociado a uno o varios usuarios
class Vehiculo(models.Model):
    patente = models.CharField(max_length=10, unique=True)  # Id del vehículo
    usuarios = models.ManyToManyField(Usuario, related_name="vehiculos", blank=True) # vincula usuario / vehiculo
    exento_global = models.BooleanField(default=False)  # exento total
    exento_parcial = models.ManyToManyField("Subcuadra", blank=True)  # Exenciones específicas

    def __str__(self):
        return self.patente

    def esta_exento_en(self, subcuadra):
        if self.exento_global:
            return True
        return self.exento_parcial.filter(id=subcuadra.id).exists()


# 🏙️ Subcuadra representa una altura específica de una calle
class Subcuadra(models.Model):
    calle = models.CharField(max_length=100)
    altura = models.IntegerField()

    class Meta:
        unique_together = ("calle", "altura")

    def __str__(self):
        return f"{self.calle}.{self.altura}"

# 💰 Tarifa por hora de estacionamiento
class Tarifa(models.Model):
    precio_por_hora = models.DecimalField(max_digits=6, decimal_places=2)  # Precio unitario

    def __str__(self):
        return f"${self.precio_por_hora}/hora"


# 🅿️ Estacionamiento en vía pública
class Estacionamiento(models.Model):
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE)
    subcuadra = models.ForeignKey(Subcuadra, on_delete=models.CASCADE)
    hora_inicio = models.DateTimeField(default=timezone.now)
    hora_fin = models.DateTimeField(null=True, blank=True)
    costo = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    activo = models.BooleanField(default=True)
    registrado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="estacionamientos_registrados"
    )

    def __str__(self):
        return f"{self.vehiculo.patente} en {self.subcuadra}"

    def finalizar(self, estrategia=None):
        """
        Finaliza el estacionamiento y calcula el costo.
        """
        from .estrategias import EstrategiaExencion
        self.hora_fin = timezone.now()
        duracion = (self.hora_fin - self.hora_inicio).total_seconds() / 3600

        if estrategia is None:
            estrategia = EstrategiaExencion()

        costo = estrategia.calcular(self.vehiculo, self.subcuadra, duracion)
        self.costo = Decimal(str(round(costo, 2)))  # siempre Decimal
        self.activo = False
        self.save()
        return self.costo

    
# 🚨 Infracción generada por un inspector
class Infraccion(models.Model):
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE)
    inspector = models.ForeignKey(Usuario, on_delete=models.CASCADE)  # 👈 obligatorio
    subcuadra = models.ForeignKey(Subcuadra, on_delete=models.CASCADE, null=True, blank=True)
    motivo = models.CharField(max_length=255, default="Impago")
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Infracción de {self.vehiculo.patente} por {self.motivo}"
    
# 🔔 Notificación enviada a un usuario
class Notificacion(models.Model):
    destinatario = models.ForeignKey(Usuario, on_delete=models.CASCADE)  # Usuario que recibe la notificación
    mensaje = models.TextField()  # Texto del mensaje
    fecha = models.DateTimeField(auto_now_add=True)  # Fecha de creación
    leida = models.BooleanField(default=False)  # Flag para saber si fue leída

    def __str__(self):
        return f"Notificación para {self.destinatario.email}"