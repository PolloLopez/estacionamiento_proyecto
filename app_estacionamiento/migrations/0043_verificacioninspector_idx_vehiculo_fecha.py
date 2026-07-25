"""
Migración 0043 — Índice compuesto VerificacionInspector (2026-07-24)

La query más frecuente sobre esta tabla es:
    VerificacionInspector.objects.filter(vehiculo=v).order_by("-fecha").first()

Postgres tiene índice automático en vehiculo_id (FK), pero para el ORDER BY -fecha
tiene que ordenar todos los registros del vehículo en memoria antes de devolver el primero.

Con 3 inspectores × 100 checks/día × 250 días laborables = ~75.000 registros/año,
el impacto se hace perceptible antes del primer año de producción real.

Este índice compuesto (vehiculo_id, fecha DESC) permite que Postgres resuelva
la query con un Index Scan + LIMIT 1 en vez de sort + full scan.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app_estacionamiento", "0042_auditoria_db_constraints_y_campos"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="verificacioninspector",
            index=models.Index(
                fields=["vehiculo", "-fecha"],
                name="idx_verificacion_vehiculo_fecha",
            ),
        ),
    ]
