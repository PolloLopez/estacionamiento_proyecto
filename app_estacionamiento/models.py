# app_estacionamiento/models.py

from django.contrib.auth.models import AbstractUser
from django.contrib.auth.base_user import BaseUserManager
from django.db import models
from django.utils import timezone
from decimal import Decimal

# 👤 Usuario del sistema (con roles y saldo)
class UsuarioManager(BaseUserManager):
    def create_user(self, correo=None, email=None, password=None, **extra_fields):
        # aceptar ambos nombres
        correo = correo or email
        if not correo:
            raise ValueError("El correo es obligatorio")
        correo = self.normalize_email(correo)
        user = self.model(correo=correo, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, correo=None, email=None, password=None, **extra_fields):
        correo = correo or email
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("es_admin", True)
        return self.create_user(correo, password, **extra_fields)


class Usuario(AbstractUser):
    username = None
    correo = models.EmailField(unique=True)
    nombre = models.CharField(max_length=25, null=True, blank=True)
    saldo = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    es_conductor = models.BooleanField(default=True)
    es_inspector = models.BooleanField(default=False)
    es_vendedor = models.BooleanField(default=False)
    es_admin = models.BooleanField(default=False)

    USERNAME_FIELD = "correo"
    REQUIRED_FIELDS = []

    objects = UsuarioManager()

    def __str__(self):
        return self.correo


# 🚗 Vehículo asociado a uno o varios usuarios
class Vehiculo(models.Model):
    patente = models.CharField(max_length=10, unique=True) 
    usuarios = models.ManyToManyField(Usuario, related_name="vehiculos", blank=True)  # vincula usuario / vehiculo
    exento_global = models.BooleanField(default=False)  # exento total
    subcuadras_exentas = models.ManyToManyField("Subcuadra", blank=True)  # Exenciones específicas
    exento_parcial = subcuadras_exentas  # alias para que los tests no fallen

    def __str__(self):
        return self.patente

    def esta_exento_en(self, subcuadra):
        if self.exento_global:
            return True
        return self.subcuadras_exentas.filter(id=subcuadra.id).exists()

    @property
    def exento_parcial(self):
        # alias para compatibilidad con tests
        return self.subcuadras_exentas
    

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
    vehiculo = models.ForeignKey("Vehiculo", on_delete=models.CASCADE)
    subcuadra = models.ForeignKey("Subcuadra", on_delete=models.CASCADE)
    hora_inicio = models.DateTimeField(default=timezone.now)
    hora_fin = models.DateTimeField(null=True, blank=True)
    costo = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    activo = models.BooleanField(default=True)
    registrado_por = models.ForeignKey(Usuario, on_delete=models.CASCADE, default=1)

    def calcular_costo(self):
        if not self.activo:
            return Decimal("0.00")
        hora_fin = timezone.now()
        duracion_horas = (hora_fin - self.hora_inicio).total_seconds() / 3600
        tarifa = Tarifa.objects.first()
        if not tarifa:
            horas_redondeadas = Decimal(str(duracion_horas)).quantize(Decimal("1"))
            return horas_redondeadas * Decimal("100.00")
        costo = Decimal(str(duracion_horas)) * Decimal(str(tarifa.precio_por_hora))
        return costo.quantize(Decimal("0.01"))

    def finalizar(self):
        """Cierra el estacionamiento, guarda costo y devuelve el valor."""
        if not self.activo:
            return Decimal("0.00")
        self.hora_fin = timezone.now()
        costo = self.calcular_costo()
        self.costo = costo
        self.activo = False
        self.save()
        return costo
    
    
# 🚨 Infracción generada por un inspector
class Infraccion(models.Model):
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE)
    inspector = models.ForeignKey(Usuario, on_delete=models.CASCADE)  # 👈 obligatorio
    subcuadra = models.ForeignKey(Subcuadra, on_delete=models.CASCADE, null=True, blank=True)
    motivo = models.CharField(max_length=255, default="Impago")
    fecha = models.DateTimeField(auto_now_add=True)
    cancelada = models.BooleanField(default=False)


    def __str__(self):
        return f"Infracción de {self.vehiculo.patente} por {self.motivo}"
    
# 🔔 Notificación enviada a un usuario
class Notificacion(models.Model):
    destinatario = models.ForeignKey(Usuario, on_delete=models.CASCADE)  # Usuario 
    mensaje = models.TextField()  
    fecha = models.DateTimeField(auto_now_add=True)  
    leida = models.BooleanField(default=False)  

    def __str__(self):
        # Usamos 'correo' porque los tests esperan ese campo en Usuario
        return f"Notificación para {self.destinatario.correo}"