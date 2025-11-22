# ESTACIONAMIENTO_APP/app_estacionamiento/urls.py
# Archivo de rutas principales del sistema.
# Cada path define una URL y la vista que se ejecuta.

from django.urls import path
from . import views

urlpatterns = [
    # 🔹 Home general del sitio
    path('', views.home, name='inicio'),

    # =========================
    # USUARIOS
    # =========================
    path('usuarios/', views.inicio_usuarios, name='inicio_usuarios'),
    path('usuarios/estacionar/', views.estacionar_vehiculo, name='usuarios_estacionar_vehiculo'),
    path('usuarios/finalizar/<int:estacionamiento_id>/', views.finalizar_estacionamiento, name='usuarios_finalizar_estacionamiento'),
    path('usuarios/cargar-saldo/', views.cargar_saldo, name='usuarios_cargar_saldo'),
    path('usuarios/historial/', views.historial_estacionamientos, name='usuarios_historial_estacionamientos'),
    path('usuarios/infracciones/', views.historial_infracciones, name='usuarios_historial_infracciones'),

    # =========================
    # INSPECTORES
    # =========================
    path('inspectores/', views.panel_inspectores, name='inspectores_panel'),
    path('inspectores/verificar/', views.verificar_vehiculo, name='inspectores_verificar_vehiculo'),
    path('inspectores/registrar/', views.registrar_estacionamiento_manual, name='inspectores_registrar_estacionamiento_manual'),
    path('inspectores/infraccion/', views.registrar_infraccion, name='inspectores_registrar_infraccion'),
    path('inspectores/resumen-cobros/', views.resumen_cobros, name='inspectores_resumen_cobros'),
    path('inspectores/resumen-infracciones/', views.resumen_infracciones, name='inspectores_resumen_infracciones'),

    # =========================
    # VENDEDORES
    # =========================
    path('vendedores/', views.panel_vendedores, name='vendedores_panel'),
    path('vendedores/estacionar/', views.registrar_estacionamiento_vendedor, name='vendedores_estacionar'),
    path('vendedores/resumen/', views.resumen_caja, name='vendedores_resumen_caja'),

    # =========================
    # INICIO / LOGIN / LOGOUT
    # =========================
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
]
