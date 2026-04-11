# app_estacionamiento/models.py


import math
from decimal import Decimal
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.base_user import BaseUserManager
from django.db import models
from django.utils import timezone
from datetime import timedelta

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
        if not correo:
            raise ValueError("El correo es obligatorio")

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("es_admin", True)

        return self.create_user(correo=correo, password=password, **extra_fields)

class Municipio(models.Model):
    nombre = models.CharField(max_length=100)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre


class Usuario(AbstractUser):
    objects = UsuarioManager()  # 👈 ESTO ES CLAVE

    username = None
    correo = models.EmailField(unique=True, null=True, blank=True)

    municipio = models.ForeignKey(
    Municipio,
    on_delete=models.CASCADE,
    null=True,
    blank=True
    )

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

    def __str__(self):
        return self.patente

    def esta_exento_en(self, subcuadra):
        if self.exento_global:
            return True
        return self.subcuadras_exentas.filter(id=subcuadra.id).exists()   

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

        print("💾 SAVE EJECUTADO")
        print("ID:", self.id)
        print("ACTIVO:", self.activo)
        print("STACK TRACE 👇")
        traceback.print_stack(limit=5) 

        if not self.municipio and self.registrado_por:
            self.municipio = self.registrado_por.municipio 

        super().save(*args, **kwargs)

    def finalizar(self):
        print("🔥 FINALIZAR EJECUTADO")

        if not self.activo:
            print("⚠️ YA ESTABA FINALIZADO")
            return self.costo

        self.hora_fin = timezone.now()

        costo = self.calcular_costo()

        self.costo = costo
        self.activo = False

        print("💾 GUARDANDO FINALIZACION...")
        self.save()

        print("✅ FINALIZADO OK")

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

# 🚨 Infracción generada por un inspector
class Infraccion(models.Model):
    municipio = models.ForeignKey(
        Municipio,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

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

# 🔔 Notificación enviada a un usuario
class Notificacion(models.Model):
    destinatario = models.ForeignKey(Usuario, on_delete=models.CASCADE)  # Usuario 
    mensaje = models.TextField()  
    fecha = models.DateTimeField(auto_now_add=True)  
    leida = models.BooleanField(default=False)  

    def __str__(self):
        # Usamos 'correo' porque los tests esperan ese campo en Usuario
        return f"Notificación para {self.destinatario.correo}"