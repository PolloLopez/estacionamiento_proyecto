Esta carpeta tiene un sistema de gestion de estacionamiento ciudadana, ventas, cobros, infracciones, excenciones totales y parciales.
Explicando cada funcion y con nombres posiblemente bien descriptivos y en castellano

## Ramas Git

- `main` → producción (Railway despliega desde acá). Solo recibe merges desde `develop`.
- `develop` → rama de trabajo activa. Todo feature nuevo va acá.

Flujo de trabajo:
1. Desarrollar y commitear en `develop`
2. Cuando el feature está listo y probado localmente: `git checkout main && git merge develop && git push`
3. Railway despliega automáticamente desde `main`

Crear las ramas (una sola vez desde PowerShell):
```powershell
git checkout -b develop
git push -u origin develop
```