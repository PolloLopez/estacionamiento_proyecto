from django.contrib import admin
from .models import Comentario

@admin.register(Comentario)
class ComentarioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'texto', 'fecha')
    search_fields = ('nombre', 'texto')
    list_filter = ('fecha',)
    ordering = ('-fecha',)