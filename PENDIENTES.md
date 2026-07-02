# Pendientes y bugs — Sistema de Estacionamiento
**Última actualización:** 2026-06-10 | **Entorno:** estacionamiento.up.railway.app

---

## ✅ RESUELTOS (esta sesión)

- [x] Menú hamburguesa no redirigía → `pointer-events:none` en backdrop + document listener
- [x] MercadoPago Error 400 `invalid_auto_return` → eliminado `auto_return` de la preferencia
- [x] Botón "Pagar y finalizar" sin estilo (invisible) → `class="btn"` corregido
- [x] Estacionamiento vencido que no se podía finalizar → era consecuencia del botón invisible
- [x] "No autorizado" en texto plano → template `403.html` con navbar y botones de volver
- [x] `NoReverseMatch caja_inspector` crasheaba vistas inspector → corregido a `inspectores_caja`
- [x] `resumen_cobros` / `resumen_infracciones` con campos incorrectos → corregidos
- [x] Tabla historial estacionamientos desbordaba contenedor → `overflow-x:auto`
- [x] Botón "Entrar" sin estilo en login → `class="btn"`
- [x] Google OAuth `redirect_uri_mismatch` → nuevo cliente OAuth creado + URI autorizada
- [x] `DoesNotExist: Site matching query` → `SITE_ID=2` en settings desde variable de entorno
- [x] Branding por municipio (logo + colores + nombre_sistema) → campo en modelo + context processor
- [x] Logo navbar muy grande en mobile → CSS `font-size:0.88rem` con ellipsis en ≤768px
- [x] Título de pestaña "Login" → "Estacionamiento — Ingresar"
- [x] Migración 0028 → corrige help_texts y `verbose_name="ID"` pendientes de 0027
- [x] Deploy Railway desconectado al migrar repo de cuenta → reconectado a PolloLopez

---

## 🔴 CRÍTICO

- [ ] **SITE_ID en Railway**: agregar variable `SITE_ID=2` en Railway → Variables
  (el código ya lo lee del entorno, pero la variable debe estar seteada)

---

## 🟡 FUNCIONAL — CONDUCTOR

- [ ] estando logueado como usuario y querer ir al inicio: ".../usuarios/inicio/"  rompe
- [ ] Timer en inicio muestra NaN:NaN (error de parsing de fecha en JS)
- [ ] Descuento de saldo debe ser al "Estacionar" al finalizar, aparece pagar y finalizar
- [ ] Usuario creado por Google OAuth no carga correctamente nombre y apellido, al ingresar por primera vez con google dirigir a completar sus datos

---

## 🟡 FUNCIONAL — INSPECTOR

- [ ] Subcuadras vacías al registrar infracción (falta datos de prueba o bug en queryset)

---

## 🟡 FUNCIONAL — VENDEDOR

- [ ] Cobrar infracciones por patente (funcionalidad no implementada)
- [ ] Selector de período al cerrar caja (diario / semanal / mensual)

---

## 🔵 MEJORAS

- [ ] Pantalla de consentimiento de Google OAuth: completar campos (logo, descripción, dominio verificado)
- [ ] Modo alto contraste / uso en exterior con sol
- [ ] Separar `settings_dev.py` / `settings_prod.py`
- [ ] Tests de integración para flujo MP (webhook)

---

## 📋 ORDEN SUGERIDO

1. Agregar `SITE_ID=2` en Railway variables (5 min)
2. Completar pantalla de consentimiento Google (para que no muestre "app no verificada")
3. Marcar `es_conductor=True` en usuarios Google OAuth
4. Timer NaN:NaN
5. Subcuadras en inspector
6. Cobrar infracciones en vendedor
7. MercadoPago producción
