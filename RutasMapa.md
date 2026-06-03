# 🗺️ Mapa de rutas actual (Django)

## 🔹 Root / Core

- `/` → redirect por rol (`inicio`)

---

## 🔐 Auth

- `/usuarios/login/` → login_view (name: `login`)
- `/usuarios/logout/` → logout_view (name: `logout`)
- `/usuarios/registro/` → registro_view (name: `registro`)

---

## 👤 Usuarios (Conductores)

- `/usuarios/inicio/` → inicio_usuarios (name: `inicio`)
- `/usuarios/historial/` → historial_estacionamientos (name: `historial_estacionamientos`)
- `/usuarios/estacionar/` → estacionar_vehiculo (name: `usuarios_estacionar_vehiculo`)
- `/usuarios/finalizar/<id>/` → finalizar_estacionamiento (name: `usuarios_finalizar_estacionamiento`)
- `/usuarios/mis-estacionamientos/` → mis_estacionamientos
- `/usuarios/infracciones/` → usuarios_infracciones
- `/usuarios/deuda/` → consultar_deuda

---

## 👮 Inspectores

- `/usuarios/inspectores/` → panel_inspectores (name: `panel_inspectores`)
- `/usuarios/inspectores/verificar/` → verificar_vehiculo
- `/usuarios/inspectores/infraccion/` → registrar_infraccion
- `/usuarios/inspectores/manual/` → registrar_estacionamiento_manual
- `/usuarios/inspectores/resumen/` → resumen_infracciones
- `/usuarios/inspectores/cobros/` → resumen_cobros
- `/usuarios/inspectores/cerrar-caja/` → cerrar_caja

---

## 💰 Vendedores

- `/usuarios/vendedores/` → panel_vendedor (name: `panel_vendedor`)
- `/usuarios/vendedores/registrar/` → registrar_estacionamiento_vendedor
- `/usuarios/vendedores/resumen/` → resumen_caja

---

## 🛠 Admin

- `/usuarios/admin-panel/` → panel_admin (name: `panel_admin`)
- `/usuarios/admin-exenciones/` → panel_exenciones

---

## 🎟 Tickets

- `/inspectores/ticket/<id>/` → ticket_infraccion
- `/inspectores/ticket-cobro/<id>/` → ticket_cobro

---

## ⚙️ Otros

- `/vehiculo/agregar/` → agregar_vehiculo
- `/inspectores/caja/` → caja_inspector