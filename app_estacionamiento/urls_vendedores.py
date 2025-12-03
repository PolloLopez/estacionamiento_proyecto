# app_estacionamiento/tests/urls_vendedores.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.panel_vendedores, name='panel_vendedores'),
    path('registrar/', views.registrar_estacionamiento_vendedor, name='registrar_estacionamiento_vendedor'),
    path('resumen-caja/', views.resumen_caja, name='resumen_caja'),
]
