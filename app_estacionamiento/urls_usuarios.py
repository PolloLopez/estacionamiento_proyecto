# ESTACIONAMIENTO_APP/app_estacionamiento/urls_usuarios.py
# Rutas específicas del usuario final

from django.urls import path
from . import views

urlpatterns = [
    path('', views.inicio_usuarios, name='inicio_usuarios'),

    # Finalizar estacionamiento
    path("finalizar/<int:estacionamiento_id>/", views.finalizar_estacionamiento, name="usuarios_finalizar_estacionamiento"),

    # Historial de estacionamientos
    path("historial/", views.usuarios_historial, name="usuarios_historial_estacionamientos"),

    # Historial de infracciones
    path("infracciones/", views.usuarios_infracciones, name="usuarios_infracciones"),

    # Estacionar vehículo
    path("estacionar/", views.estacionar_vehiculo, name="estacionar_vehiculo"),

    # Inicio de usuarios
    path("inicio/", views.inicio_usuarios, name="inicio_usuarios"),

    # Cargar saldo
    path("cargar-saldo/", views.cargar_saldo_usuario, name="usuarios_cargar_saldo"),
]  