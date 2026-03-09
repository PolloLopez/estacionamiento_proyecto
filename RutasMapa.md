# Mapa de rutas actual (Django)

## 1) Rutas activas (definidas en `sitio/urls.py`)

### Home / Auth
- `/` → `app_estacionamiento.views.inicio` (name: `inicio`)
- `/home/` → `app_estacionamiento.views.home` (name: `home`)

### Usuarios
- `/usuarios/login/` → `app_estacionamiento.views.login_view` (name: `login`)
- `/usuarios/inicio/` → `app_estacionamiento.views.inicio_usuarios` (name: `inicio_usuarios`)
- `/usuarios/logout/` → `app_estacionamiento.views.logout_view` (name: `logout`)

- `/usuarios/estacionar/` → `app_estacionamiento.views.estacionar_vehiculo` (name: `usuarios_estacionar_vehiculo`)
- `/usuarios/finalizar/<int:estacionamiento_id>/` → `app_estacionamiento.views.finalizar_estacionamiento` (name: `usuarios_finalizar_estacionamiento`)
- `/usuarios/historial/` → `app_estacionamiento.views.historial_estacionamientos` (name: `usuarios_historial_estacionamientos`)
- `/usuarios/infracciones/` → `app_estacionamiento.views.usuarios_infracciones` (name: `usuarios_historial_infracciones`)
- `/usuarios/cargar_saldo/` → `app_estacionamiento.views.cargar_saldo_usuario` (name: `usuarios_cargar_saldo`)
- `/usuarios/deuda/` → `app_estacionamiento.views.consultar_deuda` (name: `usuarios_consultar_deuda`)

### Inspectores
- `/inspectores/verificar/` → `app_estacionamiento.views.verificar_vehiculo` (name: `inspectores_verificar_vehiculo`)
- `/inspectores/infraccion/` → `app_estacionamiento.views.registrar_infraccion` (name: `inspectores_registrar_infraccion`)
- `/inspectores/registrar-infraccion/` → `app_estacionamiento.views.registrar_infraccion` (name: `inspectores_registrar_infraccion`)  **(duplicate endpoint; misma view & name)**
- `/inspectores/panel/` → `app_estacionamiento.views.panel_inspectores` (name: `panel_inspectores`)

- `/inspectores/registrar_manual/` → `app_estacionamiento.views.registrar_estacionamiento_manual` (name: `inspectores_registrar_estacionamiento_manual`)
- `/inspectores/resumen_cobros/` → `app_estacionamiento.views.resumen_cobros` (name: `inspectores_resumen_cobros`)
- `/inspectores/resumen_infracciones/` → `app_estacionamiento.views.resumen_infracciones` (name: `inspectores_resumen_infracciones`)

### Vendedores
- `/vendedores/panel/` → `app_estacionamiento.views.panel_vendedores` (name: `panel_vendedores`)
- `/vendedores/registrar/` → `app_estacionamiento.views.registrar_estacionamiento_vendedor` (name: `vendedores_registrar_estacionamiento`)
- `/vendedores/resumen/` → `app_estacionamiento.views.resumen_caja` (name: `vendedores_resumen_caja`)

### Admin municipal (no es Django admin)
- `/panel-admin/` → `app_estacionamiento.views.panel_admin` (name: `panel_admin`)
- `/admin/cargar_saldo/<int:usuario_id>/` → `app_estacionamiento.views.cargar_saldo` (name: `cargar_saldo`)

### Django admin
- `/admin/` → `django.contrib.admin.site.urls`

---

## 2) Rutas duplicadas / conflictuosas (revisar y limpiar)

- `/inspectores/verificar/` aparece **dos veces** en `sitio/urls.py` (misma vista). Esto no rompe el sistema, pero es redundante.
- `/inspectores/infraccion/` aparece **dos veces** en `sitio/urls.py` (misma vista y mismo nombre). Recomendación: eliminar duplicados.
- El nombre `inspectores_registrar_infraccion` está definido dos veces (duplica nombre de URL).

---

## 3) Rutas no usadas / módulos de URLs “huérfanos”

Los siguientes archivos tienen `urlpatterns`, pero **no están incluidos** en `sitio/urls.py` ni en ningún otro lugar, por lo que **no afectan la aplicación activa**:

- `app_estacionamiento/urls.py` (contiene rutas de home/login/inicio/logout)
- `app_estacionamiento/urls_inspectores.py` (panel, verificar, registrar infracción, etc.)
- `app_estacionamiento/urls_usuarios.py` (inicio usuario, historial, cargar saldo, etc.)
- `app_estacionamiento/urls_vendedores.py` (panel vendedor, registrar, resumen)
- `app_estacionamiento/urls_admin_custom.py` (panel admin y gestión de roles/tarifas/infracciones)

✅ Estos archivos son candidatos a:
- Ser eliminados si no se van a usar, o
- Ser integrados mediante `include()` en `sitio/urls.py` para organizar mejor las rutas.

---

## 4) Recomendación inmediata para ordenar rutas

1. **Eliminar duplicados** en `sitio/urls.py` (inspectores verificar / infraccion).  
2. **Decidir un único patrón**: si querés dividir por rol, conviene usar `include()` y mantener cada `urls_*` por rol; si no, mantener todo en `sitio/urls.py` y borrar los `urls_*` huérfanos.
3. **Renombrar/normalizar nombres** de rutas para que sigan un patrón consistente (ej. `inspectores/` + `...` / `usuarios/` + `...`).

---

✅ **Siguiente paso sugerido**: dime si querés que implemente (1) la limpieza de duplicados en `sitio/urls.py` o (2) refactorizar para un esquema basado en `include()` y módulos de URL por rol. Estoy listo para hacer el cambio y dejar la estructura ordenada.