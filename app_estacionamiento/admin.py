#app_estacionamiento/admin.py

from django.contrib import admin
from .models import Usuario, Vehiculo, Subcuadra, Tarifa, Estacionamiento, Infraccion, Notificacion

@admin.register(Vehiculo)
class VehiculoAdmin(admin.ModelAdmin):
    list_display = ("patente", "exento_global")
    search_fields = ("patente",)
    filter_horizontal = ("subcuadras_exentas",)

@admin.register(Subcuadra)
class SubcuadraAdmin(admin.ModelAdmin):
    list_display = ("calle", "altura", "municipio")
    list_filter = ("municipio", "calle")
    search_fields = ("calle",)
    
admin.site.register(Usuario)
admin.site.register(Tarifa)
admin.site.register(Estacionamiento)
admin.site.register(Infraccion)
admin.site.register(Notificacion)
