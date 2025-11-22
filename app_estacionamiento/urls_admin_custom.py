# ESTACIONAMIENTO_APP/app_estacionamiento/urls_admin_custom.py
# Archivo: urls_admin_custom.py
# Panel de administración del sistema

from django.urls import path
from . import views

urlpatterns = [
    path('', views.inicio_admin, name='inicio_admin'),
    path('usuarios/', views.gestionar_usuarios, name='gestionar_usuarios'),
    path('inspectores/', views.gestionar_inspectores, name='gestionar_inspectores'),
    path('vendedores/', views.gestionar_vendedores, name='gestionar_vendedores'),
    path('tarifas/', views.gestionar_tarifas, name='gestionar_tarifas'),
    path('horarios/', views.gestionar_horarios, name='gestionar_horarios'),
    path('infracciones/', views.gestionar_infracciones, name='gestionar_infracciones_admin'),
]
