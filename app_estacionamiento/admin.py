#app_estacionamiento/admin.py

from django.contrib import admin
from .models import Usuario, Estacionamiento, Notificacion

admin.site.register(Usuario)
admin.site.register(Estacionamiento)
admin.site.register(Notificacion)
