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
    exento_global = models.BooleanField(default=False)
    exento_parcial = models.BooleanField(default=False)
    subcuadras_exentas = models.ManyToManyField("Subcuadra", blank=True)
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
        # Zona Única (altura=0) no muestra el número
        if self.altura == 0:
            return self.calle
        return f"{self.calle} {self.altura}"
    
class Estado(models.TextChoices):
    ACTIVO = "ACTIVO", "Activo"
    FINALIZADO = "FINALIZADO", "Finalizado"

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

class Estacionamiento(models.Model):
    vehiculo = models.ForeignKey("Vehiculo", on_delete=models.CASCADE)
    subcuadra = models.ForeignKey("Subcuadra", on_delete=models.PROTECT)

    usuario = models.ForeignKey(
        "Usuario",
        on_delete=models.PROTECT,
        null=True
    )

    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.ACTIVO
    )

    hora_inicio = models.DateTimeField(auto_now_add=True)
    hora_fin = models.DateTimeField(null=True, blank=True)

    duracion_min = models.IntegerField(default=60)

    costo_base = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    costo_final = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    creado_en = models.DateTimeField(auto_now_add=True)

    @property
    def activo(self):
        return self.estado == Estado.ACTIVO

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["vehiculo"],
                condition=Q(estado="ACTIVO"),
                name="unique_estacionamiento_activo_por_vehiculo",
            )
        ]

class MovimientoCaja(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    tipo = models.CharField(max_length=10)  # egreso / ingreso
    descripcion = models.TextField(blank=True, null=True)
    cerrado = models.BooleanField(default=False)
    creado_en = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.pk:
            original = MovimientoCaja.objects.get(pk=self.pk)
            if original.cerrado:
                raise Exception("No se puede modificar un movimiento cerrado")
        super().save(*args, **kwargs)
    
class CierreCaja(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)

    total_cobrado = models.DecimalField(max_digits=10, decimal_places=2)

    fecha_apertura = models.DateTimeField()
    fecha_cierre = models.DateTimeField(auto_now_add=True)

    cantidad_movimientos = models.IntegerField(default=0)

    # auditoria
    creado_en = models.DateTimeField(default=timezone.now)
    creado_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name="cierres_creados")

    def __str__(self):
        return f"Cierre {self.usuario} - {self.total_cobrado}"

class VerificacionInspector(models.Model):
    inspector = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE)
    subcuadra = models.ForeignKey(Subcuadra, on_delete=models.CASCADE)
    fecha = models.DateTimeField(auto_now_add=True)
    infraccion_generada = models.BooleanField(default=False)
    resultado = models.CharField(max_length=50)

class Infraccion(models.Model):
    municipio = models.ForeignKey(Municipio, on_delete=models.CASCADE, null=True, blank=True)
    estado = models.CharField(max_length=20, choices=[("pendiente", "Pendiente"), ("pagada", "Pagada"), ("anulada", "Anulada")], default="pendiente")
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE)
    inspector = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    subcuadra = models.ForeignKey(Subcuadra, on_delete=models.CASCADE, null=True, blank=True)
    estacionamiento = models.ForeignKey(Estacionamiento, on_delete=models.SET_NULL, null=True, blank=True)
    motivo = models.CharField(max_length=255, default="Impago")
    foto = models.ImageField(upload_to="infracciones/", null=True, blank=True)
    qr_code = models.CharField(max_length=255, null=True, blank=True)
    monto = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    creado_en = models.DateTimeField(auto_now_add=True)   # única fecha de creación
    fecha_pago = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.municipio:
            if self.inspector and self.inspector.municipio:
                self.municipio = self.inspector.municipio
            elif self.subcuadra and self.subcuadra.municipio:
                self.municipio = self.subcuadra.municipio

        super().save(*args, **kwargs)

# 🔔 Notificación enviada a un usuario
class Notificacion(models.Model):
    destinatario = models.ForeignKey(Usuario, on_delete=models.CASCADE)  # Usuario 
    mensaje = models.TextField()  
    fecha = models.DateTimeField(auto_now_add=True)  
    leida = models.BooleanField(default=False)  

    def __str__(self):
        # Usamos 'correo' porque los tests esperan ese campo en Usuario
        return f"Notificación para {self.destinatario.correo}"