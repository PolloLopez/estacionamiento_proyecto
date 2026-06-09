# Pendientes y bugs detectados en produccion
**Fecha:** 2026-06-08 | **Entorno:** web-production-78866.up.railway.app

---

## CRITICO

### Admin no puede entrar
- [ ] Diagnosticar por que admin@ejemplo.com no puede acceder al panel admin
- Posible causa: sesion vieja, rol no seteado, o redireccion incorrecta

---

## CONDUCTOR

### Estilos
- [ ] Fondo verde oscuro opaca el texto de cantidad de horas al estacionar
- [ ] Revisar contraste general para uso en exterior con luz solar
- [ ] Evaluar agregar modo oscuro / modo alto contraste

### Funcionalidad
- [ ] Timer muestra NaN:NaN al estacionar (error en JS, posiblemente fecha no parseable)
- [ ] Carga de saldo con MercadoPago no funciona (pendiente configurar MP sandbox en Railway)

---

## INSPECTOR

### Funcionalidad
- [ ] No ve subcuadras al registrar infraccion (dropdown vacio o sin datos)
- [ ] No puede ver historial de infracciones
- [ ] No puede cerrar caja

### Consulta respondida
- Las infracciones que ve el inspector son las que EL genero
- "No pagadas" = infracciones que aun no fueron abonadas por el conductor
  (no tiene relacion con tolerancia; tolerancia aplica al estacionamiento vencido)

---

## VENDEDOR

### Funcionalidad
- [ ] No puede cargar estacionamiento (conductor sin saldo, admin no disponible para gestionarlo)
- [ ] Falta "cobrar infracciones" por patente:
  - Buscar infraccion por patente
  - Cobrarla y acreditarla en la caja del vendedor (igual que inspector)
- [ ] Al cerrar caja: definir periodo del cierre (diario / semanal / mensual)

---

## MEJORAS GENERALES

- [ ] Estilos: visibilidad en sol / exterior para adultos y jovenes
- [ ] Modo oscuro o alto contraste
- [ ] Cierre de caja con selector de periodo (diario/semanal/mensual)

---

## EN PROGRESO

- [x] Deploy en Railway - COMPLETADO
- [x] Base de datos PostgreSQL conectada
- [x] Login con email/password funciona
- [ ] Google OAuth - EN PROGRESO
- [ ] Crear usuarios iniciales en produccion (script pendiente por DATABASE_URL en consola)

---

## ORDEN SUGERIDO DE TRABAJO

1. Configurar Google OAuth (en progreso)
2. Diagnosticar acceso admin
3. Crear usuarios iniciales en produccion
4. Bugs funcionales (timer, subcuadras, caja)
5. Cobrar infracciones en vendedor
6. Estilos / contraste / modo oscuro
7. MercadoPago sandbox
