#app_estacionamiento/models.py
from django.db import models
from django.utils import timezone
from datetime import timedelta

# 👤 Usuario del sistema (conductor o inspector)
class Usuario(models.Model):
    nombre = models.CharField(max_length=100)
    correo = models.EmailField(unique=True)
    saldo = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    es_inspector = models.BooleanField(default=False)  # distingue inspectores

    def __str__(self):
        return self.nombre

# 🚗 Vehículo asociado a uno o varios usuarios
class Vehiculo(models.Model):
    patente = models.CharField(max_length=20, unique=True)
    usuarios = models.ManyToManyField(Usuario, related_name='vehiculos')
    exento_en_zona = models.BooleanField(default=False)
    subcuadras_exentas = models.ManyToManyField('Subcuadra', blank=True)

    def __str__(self):
        return self.patente

    def esta_exento_en(self, subcuadra):
        """
        Verifica si el vehículo está exento en esta subcuadra.
        # acá se implementa Strategy
        """
        if self.exento_en_zona:
            return True
        return self.subcuadras_exentas.filter(id=subcuadra.id).exists()

# 🏙️ Subcuadra representa una altura específica de una calle
class Subcuadra(models.Model):
    calle = models.CharField(max_length=100)  # Ej: "Calle 21"
    altura = models.IntegerField()            # Ej: 300, 350, etc.

    def __str__(self):
        return f"{self.calle}.{self.altura}"

# 💰 Tarifa por hora
class Tarifa(models.Model):
    precio_por_hora = models.DecimalField(max_digits=6, decimal_places=2)

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

    def __str__(self):
        return f"{self.vehiculo.patente} en {self.subcuadra}"

    def finalizar(self, estrategia=None):
        """
        Finaliza el estacionamiento y calcula el costo usando una estrategia.
        # acá se implementa Strategy
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
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE)
    inspector = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    subcuadra = models.ForeignKey(Subcuadra, on_delete=models.CASCADE)
    estacionamiento = models.ForeignKey(Estacionamiento, on_delete=models.CASCADE, null=True, blank=True)
    fecha = models.DateTimeField(default=timezone.now)
    cancelada = models.BooleanField(default=False)
    notificada = models.BooleanField(default=False)

    def __str__(self):
        return f"Infracción a {self.vehiculo.patente} por {self.inspector.nombre}"

    def verificar_cancelacion(self):
        """
        Verifica si el estacionamiento fue pagado dentro de los 15 minutos.
        # acá se implementa Strategy
        """
        if self.estacionamiento and self.estacionamiento.hora_fin:
            diferencia = self.estacionamiento.hora_fin - self.fecha
            if diferencia.total_seconds() <= 900:
                self.cancelada = True
                self.save()
                return "Infracción cancelada y notificada"
        return "Infracción sigue activa"
