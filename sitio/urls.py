#sitio/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('paginas.urls')),  # si tu app "paginas" existe
    path('', include('app_estacionamiento.urls')),  # esto conecta las vistas
]
