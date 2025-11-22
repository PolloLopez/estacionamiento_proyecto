# ESTACIONAMIENTO_APP/app_estacionamiento/urls_usuarios.py
# Archivo: urls_usuarios.py
# Rutas específicas del usuario final

from django.urls import path
from . import views

urlpatterns = [
    path('', views.inicio_usuarios, name='inicio_usuarios'),
    path('estacionar/', views.estacionar_vehiculo, name='estacionar_vehiculo'),
    path('finalizar/<int:estacionamiento_id>/', views.finalizar_estacionamiento, name='finalizar_estacionamiento'),
    path('historial/', views.historial_estacionamientos, name='historial_estacionamientos'),
    path('infracciones/', views.historial_infracciones, name='historial_infracciones'),
    path('cargar-saldo/', views.cargar_saldo, name='cargar_saldo'),
    path('consultar-deuda/', views.consultar_deuda, name='consultar_deuda'),
]
