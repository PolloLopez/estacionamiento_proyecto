# app_estacionamiento/forms.py

from django import forms
from .models import Usuario

class RegistroUsuarioForm(forms.ModelForm):
    password1 = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = Usuario
        fields = ["correo"]

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("password1")
        p2 = cleaned_data.get("password2")

        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Las contraseñas no coinciden")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])

        # defaults del sistema
        user.es_conductor = True
        user.es_admin = False
        user.es_inspector = False
        user.es_vendedor = False

        if commit:
            user.save()
        return user