# sitio/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from app_estacionamiento import views

urlpatterns = [
    # Home
    path("", views.inicio, name="inicio"),

    # Usuarios
    path("usuarios/login/", views.login_view, name="login"),
    path("usuarios/logout/", views.logout_view, name="logout"),
    path("usuarios/inicio/", views.inicio_usuarios, name="inicio_usuarios"),

    path("usuarios/estacionar/", views.estacionar_vehiculo, name="usuarios_estacionar_vehiculo"),
    path("usuarios/finalizar/<int:estacionamiento_id>/", views.finalizar_estacionamiento, name="usuarios_finalizar_estacionamiento"),
    path("usuarios/historial/", views.historial_estacionamientos, name="usuarios_historial_estacionamientos"),
    path("usuarios/infracciones/", views.usuarios_infracciones, name="usuarios_historial_infracciones"),
    path("usuarios/deuda/", views.consultar_deuda, name="usuarios_consultar_deuda"),

    # Inspectores
    path("inspectores/panel/", views.panel_inspectores, name="panel_inspectores"),
    path("inspectores/verificar/", views.verificar_vehiculo, name="inspectores_verificar_vehiculo"),
    path("inspectores/infraccion/", views.registrar_infraccion, name="inspectores_registrar_infraccion"),
    path("inspectores/registrar_manual/", views.registrar_estacionamiento_manual, name="inspectores_registrar_estacionamiento_manual"),
    path("inspectores/resumen_cobros/", views.resumen_cobros, name="inspectores_resumen_cobros"),
    path("inspectores/resumen_infracciones/", views.resumen_infracciones, name="inspectores_resumen_infracciones"),

    # Vendedores
    path("vendedores/panel/", views.panel_vendedores, name="panel_vendedores"),
    path("vendedores/registrar/", views.registrar_estacionamiento_vendedor, name="vendedores_registrar_estacionamiento"),
    path("vendedores/resumen/", views.resumen_caja, name="vendedores_resumen_caja"),

    # Admin municipal
    path("panel-admin/", views.panel_admin, name="panel_admin"),
    path("admin/cargar-saldo/<int:usuario_id>/", views.cargar_saldo, name="cargar_saldo"),
    path("admin/exenciones/", views.panel_exenciones, name="exenciones"),

    # Django admin
    path("admin/", admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)