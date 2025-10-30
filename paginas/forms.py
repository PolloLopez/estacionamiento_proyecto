from django import forms
from .models import Comentario

class ComentarioForm(forms.ModelForm):
    class Meta:
        model = Comentario
        fields = ['nombre', 'texto']
        widgets = {
            'nombre': forms.TextInput(attrs={'placeholder': 'Tu nombre'}),
            'texto': forms.Textarea(attrs={'placeholder': 'Escribí tu comentario'}),
        }