#app_estacionamiento/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Municipio, Usuario, Vehiculo, Subcuadra, Tarifa, Estacionamiento, Infraccion, Notificacion, VehiculoUsuario

@admin.register(Vehiculo)
class VehiculoAdmin(admin.ModelAdmin):
    list_display = ("patente", "exento_global", "municipio")
    search_fields = ("patente",)
    filter_horizontal = ("subcuadras_exentas",)

    def get_readonly_fields(self, request, obj=None):
        if not request.user.is_superuser:
            return ("exento_global", "subcuadras_exentas")
        return ()
    

class VehiculoUsuarioInline(admin.TabularInline):
    model = VehiculoUsuario
    extra = 1

@admin.register(Subcuadra)
class SubcuadraAdmin(admin.ModelAdmin):
    list_display = ("calle", "altura", "municipio")
    list_filter = ("municipio", "calle")
    search_fields = ("calle",)

@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    model = Usuario

    inlines = [VehiculoUsuarioInline]

    list_display = ("correo", "es_admin", "es_inspector", "es_conductor", "municipio")
    search_fields = ("correo",)
    ordering = ("correo",)

    fieldsets = (
        (None, {"fields": ("correo", "password")}),
        ("Información personal", {"fields": ("municipio", "saldo")}),
        ("Roles", {"fields": ("es_conductor", "es_inspector", "es_vendedor", "es_admin")}),
        ("Permisos", {"fields": ("is_active", "is_staff", "is_superuser")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("correo", "password1", "password2", "is_staff", "is_superuser"),
        }),
    )

admin.site.register(Tarifa)
admin.site.register(Estacionamiento)
admin.site.register(Infraccion)
admin.site.register(Notificacion)
admin.site.register(Municipio)
