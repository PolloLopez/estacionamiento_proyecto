#app_estacionamiento/admin.py

from django.contrib import admin
from .models import Usuario, Vehiculo, Subcuadra, Tarifa, Estacionamiento, Infraccion, Notificacion

admin.site.register(Usuario)
admin.site.register(Vehiculo)
admin.site.register(Subcuadra)
admin.site.register(Tarifa)
admin.site.register(Estacionamiento)
admin.site.register(Infraccion)
admin.site.register(Notificacion)
