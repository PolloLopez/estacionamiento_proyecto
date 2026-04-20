# app_estacionamiento/urls.py
from django.urls import path
from . import views
from .views import registro_view

urlpatterns = [
    path("", views.home, name="inicio"),
    path("usuarios/login/", views.login_view, name="login"),
    path("usuarios/inicio/", views.inicio_usuarios, name="inicio_usuarios"),
    path("usuarios/logout/", views.logout_view, name="logout"),
    path("admin/exenciones/", views.panel_exenciones, name="exenciones"),
    path("registro/", registro_view, name="registro"),
]
