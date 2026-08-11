---
name: code-review
description: Revisión de calidad y mantenibilidad con las convenciones de Leandro
---

# Revisión de Código

Actuá como ingeniero senior revisando código propio, priorizando mantenibilidad sobre elegancia. Revisá el diff de git pendiente (o si no hay cambios sin commitear, el módulo que te indique).

Buscá:
1. **Duplicación de lógica** entre vistas o funciones que podría extraerse a una función/servicio común.
2. **Nombres poco descriptivos** o en inglés donde debería ser español (según convención del proyecto).
3. **Funciones que hacen demasiado** (mezclan validación + lógica de negocio + acceso a datos) y convendría separar.
4. **Manejo de errores faltante o silencioso** (except genéricos, errores tragados sin log).
5. **Comentarios faltantes** en lógica no obvia (el porqué, no el qué).
6. **Sobreingeniería**: abstracciones o dependencias que no se justifican para el tamaño del proyecto.
7. **Inconsistencias** con el resto del código ya existente en el proyecto.

Para cada hallazgo:
- **Prioridad**: 🔴 (rompe algo o genera bugs) / 🟡 (afecta mantenibilidad) / 🟢 (mejora de estilo)
- **Archivo y línea**
- **Explicación paso a paso** de por qué conviene cambiarlo
- **Código de ejemplo** simple, sin librerías nuevas

Al final generá el resumen en formato para PENDIENTES.md.

No implementes cambios automáticamente — mostrame el listado primero.