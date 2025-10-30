# app_estacionamiento/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('cargar-saldo/', views.cargar_saldo, name='cargar_saldo'),
    path('estacionar/', views.estacionar_auto, name='estacionar_auto'),
    path('finalizar/<int:id>/', views.finalizar_estacionamiento, name='finalizar_estacionamiento'),
]
