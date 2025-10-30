from django.shortcuts import render, redirect
from .models import Comentario
from .forms import ComentarioForm

def home(request):
    return render(request, 'home.html')

def contacto(request):
    return render(request, 'contacto.html')

def sobre(request):
    return render(request, 'sobre.html')

def comentarios(request):
    if request.method == 'POST':
        form = ComentarioForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('comentarios')  # 👈 redirige para limpiar el formulario
    else:
        form = ComentarioForm()

    todos = Comentario.objects.order_by('-fecha')
    return render(request, 'comentarios.html', {'form': form, 'comentarios': todos})