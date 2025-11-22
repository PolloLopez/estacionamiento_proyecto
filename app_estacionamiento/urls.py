# ESTACIONAMIENTO_APP/app_estacionamiento/urls.py
# Archivo: app_estacionamiento/urls.py
# Punto de entrada: acá se incluyen las rutas por rol

from django.urls import path, include
from . import views

urlpatterns = [
    # Home general del sistema → redirige a home de usuario
    path('', views.home, name='inicio'),

    # Rutas separadas por rol
    path('usuarios/', include('app_estacionamiento.urls_usuarios')),
    path('inspectores/', include('app_estacionamiento.urls_inspectores')),
    path('vendedores/', include('app_estacionamiento.urls_vendedores')),
    path('panel-admin/', include('app_estacionamiento.urls_admin_custom')),
]
