from django.db import models
from django.utils import timezone


class Usuario(models.Model):
    nombre = models.CharField(max_length=100)
    correo = models.EmailField(unique=True)
    saldo = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return self.nombre


class Estacionamiento(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    patente = models.CharField(max_length=20)
    hora_inicio = models.DateTimeField(default=timezone.now)
    hora_fin = models.DateTimeField(null=True, blank=True)
    costo = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.patente} - {self.usuario.nombre}"

    def finalizar(self):
        """Finaliza el estacionamiento y calcula el costo"""
        self.hora_fin = timezone.now()
        duracion = (self.hora_fin - self.hora_inicio).total_seconds() / 3600  # horas
        self.costo = round(duracion * 100, 2)  # ejemplo: 100 por hora
        self.activo = False
        self.save()
        return self.costo


class Notificacion(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    mensaje = models.CharField(max_length=255)
    fecha = models.DateTimeField(default=timezone.now)
    leido = models.BooleanField(default=False)

    def __str__(self):
        return f"Notificación para {self.usuario.nombre}: {self.mensaje[:30]}"
