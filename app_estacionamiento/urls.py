# ESTACIONAMIENTO_APP/app_estacionamiento/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='inicio'),
    path('estacionar/', views.estacionar_auto, name='estacionar_auto'),
    path('finalizar/<int:estacionamiento_id>/', views.finalizar_estacionamiento, name='finalizar_estacionamiento'),
    path('infraccion/', views.registrar_infraccion, name='registrar_infraccion'),
]
