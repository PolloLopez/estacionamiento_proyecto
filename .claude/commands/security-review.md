---
name: security-review
description: Auditoría de seguridad con las convenciones de Leandro (prioridades 🔴🟡🟢, español)
---

# Revisión de Seguridad

Actuá como ingeniero de seguridad (AppSec) senior. Revisá el código actual (o el diff de git si hay cambios sin commitear) buscando:

1. **Credenciales expuestas**: keys, passwords o tokens hardcodeados en el código.
2. **Control de acceso débil**: endpoints o vistas sin autenticación/autorización adecuada.
3. **Validación de entradas**: falta de sanitización en formularios, queries o inputs de usuario.
4. **Inyección**: SQL injection, XSS, command injection.
5. **Configuración insegura**: valores por defecto inseguros en settings.py (SECRET_KEY, DEBUG, ALLOWED_HOSTS), permisos excesivos.
6. **Si es un proyecto Google Apps Script/Sheets**: permisos de Spreadsheet, triggers mal configurados, Web Apps expuestas sin control de acceso.

Para cada hallazgo, indicá:
- **Prioridad**: 🔴 (crítico, arreglar antes de cualquier demo/entrega) / 🟡 (importante, no bloqueante) / 🟢 (mejora recomendada)
- **Archivo y línea** donde está el problema
- **Explicación clara** de por qué es un riesgo (en castellano, paso a paso)
- **Solución sugerida** con código de ejemplo, simple y sin sobreingeniería

Al final, generá un resumen que pueda copiarse directo al `PENDIENTES.md` del proyecto, respetando el formato de prioridades que ya uso.

No implementes los fixes automáticamente — primero mostrame el listado completo para que yo decida qué corregir.