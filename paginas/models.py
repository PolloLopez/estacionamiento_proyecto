from django.db import models

class Comentario(models.Model):
    nombre = models.CharField(max_length=100)
    texto = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre} - {self.fecha.strftime('%d/%m/%Y %H:%M')}"