# app_estacionamiento/urls.py
from django.urls import path
from . import views
 
urlpatterns = [
    path("", views.home, name="home"),
    path("usuarios/login/", views.login_view, name="login"),
    path("usuarios/inicio/", views.inicio_usuarios, name="inicio_usuarios"),
    path("usuarios/logout/", views.logout_view, name="logout"),
]
