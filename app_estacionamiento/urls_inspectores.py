# ESTACIONAMIENTO_APP/app_estacionamiento/urls_inspectores.py
# Rutas del inspector

from django.urls import path
from . import views

urlpatterns = [
    path('', views.panel_inspectores, name='panel_inspectores'),
    path('verificar/', views.verificar_vehiculo, name='verificar_vehiculo'),
    path('registrar-estacionamiento/', views.registrar_estacionamiento_manual, name='registrar_estacionamiento_manual'),
    path('registrar-infraccion/', views.registrar_infraccion, name='registrar_infraccion'),
    path('resumen-cobros/', views.resumen_cobros, name='resumen_cobros'),
    path('resumen-infracciones/', views.resumen_infracciones, name='resumen_infracciones'),
]

