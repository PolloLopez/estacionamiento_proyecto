#app_estacionamiento/views.py

from django.shortcuts import render

# Ejemplo de vista simple
def home(request):
    return render(request, 'home.html')
