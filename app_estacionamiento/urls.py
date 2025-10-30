# app_estacionamiento/urls.py

from django.urls import path, include
from . import views
from django.contrib import admin

urlpatterns = [
    path('admin/', admin.site.urls),
    path('infraccion/', views.registrar_infraccion, name='registrar_infraccion'),
    path('estacionar/', views.estacionar_auto, name='estacionar_auto'),
    path('finalizar/<int:estacionamiento_id>/', views.finalizar_estacionamiento, name='finalizar_estacionamiento'),
    path('estacionamiento/', views.home, name='estacionamiento_home'),
    path('', views.home, name='home'),  # esto conecta la vista home a "/"

]
