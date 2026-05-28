# app_estacionamiento/models.py

import math
from decimal import Decimal
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.base_user import BaseUserManager
from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from django.db.models import Q, UniqueConstraint

# 👤 Usuario del sistema 
class UsuarioManager(BaseUserManager):

    def create_user(self, correo=None, email=None, password=None, **extra_fields):
        correo = correo or email

        if not correo:
            raise ValueError("El correo es obligatorio")

        correo = self.normalize_email(correo)

        extra_fields.setdefault("is_active", True)

        user = self.model(correo=correo, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, correo=None, email=None, password=None, **extra_fields):
        correo = correo or email

        if not correo:
            raise ValueError("El correo es obligatorio")

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("es_admin", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("El superuser debe tener is_staff=True")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("El superuser debe tener is_superuser=True")

        return self.create_user(correo=correo, password=password, **extra_fields)

class Usuario(AbstractUser):
    username = None

    correo = models.EmailField(unique=True)

    municipio = models.ForeignKey(
        "Municipio",
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    saldo_operativo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    vehiculos = models.ManyToManyField(
        "Vehiculo",
        through="VehiculoUsuario",
        related_name="usuarios"
    )

    saldo = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # 🎭 Roles
    es_conductor = models.BooleanField(default=True)
    es_inspector = models.BooleanField(default=False)
    es_vendedor = models.BooleanField(default=False)
    es_admin = models.BooleanField(default=False)

    # 🔐 Django admin / permisos
    #is_staff → acceso admin Django
    #es_admin → lógica de negocio
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = "correo"
    REQUIRED_FIELDS = []

    objects = UsuarioManager()

    def __str__(self):
        return self.correo or f"Usuario #{self.id}"

class Municipio(models.Model):
    nombre = models.CharField(max_length=100, blank=True)
    apellido = models.CharField(max_length=100, blank=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre
    
# 🚗 Vehículo asociado a uno o varios usuarios
class Vehiculo(models.Model):
    patente = models.CharField(max_length=10, unique=True) 
    exento_global = models.BooleanField(default=False)  # exento total
    subcuadras_exentas = models.ManyToManyField("Subcuadra", blank=True)  # Exenciones específicas
    municipio = models.ForeignKey(Municipio,on_delete=models.CASCADE,null=True,blank=True) 
    fecha_creacion = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return self.patente

    def esta_exento_en(self, subcuadra):
        if self.exento_global:
            return True
        return self.subcuadras_exentas.filter(id=subcuadra.id).exists()   

class VehiculoUsuario(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE)

    es_propietario = models.BooleanField(default=False)
    verificado = models.BooleanField(default=False)
    
    def save(self, *args, **kwargs):
        if self.es_propietario:
            VehiculoUsuario.objects.filter(
                vehiculo=self.vehiculo,
                es_propietario=True
            ).exclude(id=self.id).update(es_propietario=False)

        super().save(*args, **kwargs)

# 🏙️ Subcuadra representa una altura específica de una calle
class Subcuadra(models.Model):
    municipio = models.ForeignKey(
        Municipio,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    calle = models.CharField(max_length=100)
    altura = models.IntegerField()

    class Meta:
        unique_together = ("calle", "altura")

    def __str__(self):
        return f"{self.calle}.{self.altura}"

# 💰 Tarifa por hora de estacionamiento
class Tarifa(models.Model):
    municipio = models.ForeignKey(
        Municipio,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    precio_por_hora = models.DecimalField(max_digits=6, decimal_places=2)

    def __str__(self):
        return f"${self.precio_por_hora}/hora"

# 🅿️ Estacionamiento en vía pública
class Estacionamiento(models.Model):
    municipio = models.ForeignKey(
        Municipio,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    vehiculo = models.ForeignKey("Vehiculo", on_delete=models.CASCADE)
    subcuadra = models.ForeignKey("Subcuadra", on_delete=models.CASCADE)
    hora_inicio = models.DateTimeField(default=timezone.now)
    hora_fin = models.DateTimeField(null=True, blank=True)
    costo = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    activo = models.BooleanField(default=True)
    registrado_por = models.ForeignKey(Usuario, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        import traceback

        if settings.DEBUG:
            traceback.print_stack(limit=5) 

        if not self.municipio and self.registrado_por:
            self.municipio = self.registrado_por.municipio 

        super().save(*args, **kwargs)

    def finalizar(self):

        if not self.activo:
            return self.costo

        self.hora_fin = timezone.now()

        costo = self.calcular_costo()

        self.costo = costo
        self.activo = False

        self.save()

        return costo

    def calcular_costo(self):
        if not self.activo:
            return Decimal("0.00")

        hora_fin = timezone.now()
        duracion_horas = (hora_fin - self.hora_inicio).total_seconds() / 3600

        # Redondeo hacia arriba mínimo 1 hora
        horas_redondeadas = max(1, math.ceil(duracion_horas))

        tarifa = Tarifa.objects.first()
        if not tarifa:
            return Decimal(horas_redondeadas) * Decimal("100.00")

        costo = Decimal(horas_redondeadas) * Decimal(str(tarifa.precio_por_hora))
        return costo.quantize(Decimal("0.01"))

    def __str__(self):
        return f"{self.vehiculo.patente} - {self.subcuadra} - {self.hora_inicio}"

class Meta:
    constraints = [
        UniqueConstraint(
            fields=["vehiculo"],
            condition=Q(activo=True),
            name="unique_estacionamiento_activo_por_vehiculo"
        )
    ]

class MovimientoCaja(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    tipo = models.CharField(max_length=10)  # egreso / ingreso
    descripcion = models.TextField(blank=True, null=True)
    fecha = models.DateTimeField(auto_now_add=True)
    
# 🚨 Infracción generada por un inspector
class Infraccion(models.Model):
    municipio = models.ForeignKey(
        Municipio,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True, null=True)

    estado = models.CharField(
        max_length=20,
        choices=[
            ("pendiente", "Pendiente"),
            ("pagada", "Pagada"),
            ("anulada", "Anulada"),
        ],
        default="pendiente"
    )

    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE)
    inspector = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    subcuadra = models.ForeignKey(Subcuadra, on_delete=models.CASCADE, null=True, blank=True)
    estacionamiento = models.ForeignKey(Estacionamiento, on_delete=models.SET_NULL, null=True, blank=True)
    motivo = models.CharField(max_length=255, default="Impago")
    fecha = models.DateTimeField(auto_now_add=True)
    cancelada = models.BooleanField(default=False)
    foto = models.ImageField(upload_to="infracciones/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    qr_code = models.CharField(max_length=255, null=True, blank=True)
    monto = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        if not self.municipio:
            if self.inspector and self.inspector.municipio:
                self.municipio = self.inspector.municipio
            elif self.subcuadra and self.subcuadra.municipio:
                self.municipio = self.subcuadra.municipio

        super().save(*args, **kwargs)

class VerificacionInspector(models.Model):
    inspector = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE)
    subcuadra = models.ForeignKey(Subcuadra, on_delete=models.CASCADE)
    fecha = models.DateTimeField(auto_now_add=True)
    resultado = models.CharField(max_length=50)

class CierreCaja(models.Model):

    usuario = models.ForeignKey("Usuario", on_delete=models.CASCADE)

    fecha_inicio = models.DateTimeField(default=timezone.now)
    fecha_cierre = models.DateTimeField(auto_now_add=True)

    total_cobrado = models.DecimalField(max_digits=10, decimal_places=2)

    observaciones = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Cierre {self.usuario.correo} - {self.fecha_cierre}"
    
# 🔔 Notificación enviada a un usuario
class Notificacion(models.Model):
    destinatario = models.ForeignKey(Usuario, on_delete=models.CASCADE)  # Usuario 
    mensaje = models.TextField()  
    fecha = models.DateTimeField(auto_now_add=True)  
    leida = models.BooleanField(default=False)  

    def __str__(self):
        # Usamos 'correo' porque los tests esperan ese campo en Usuario
        return f"Notificación para {self.destinatario.correo}"