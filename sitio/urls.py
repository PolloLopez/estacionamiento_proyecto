#sitio/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('paginas.urls')),
    path('estacionamiento/', include('app_estacionamiento.urls')),
]
