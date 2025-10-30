from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('contacto/', views.contacto, name='contacto'),
    path('sobre/', views.sobre, name='sobre'),
    path('comentarios/', views.comentarios, name='comentarios'),  # 👈 nueva vista
]
