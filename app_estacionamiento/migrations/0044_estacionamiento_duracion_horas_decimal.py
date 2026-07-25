"""
Migración 0044 — Estacionamiento.duracion_horas: IntegerField → DecimalField (2026-07-25)

Bug: el campo era IntegerField pero el sistema genera duraciones en múltiplos de 0.5h
(1h, 1.5h, 2h, 2.5h...). Al guardar Decimal("1.5"), Django hacía int(Decimal("1.5")) = 1,
truncando silenciosamente. El costo se cobraba bien (DecimalField) pero la expiración
se calculaba como hora_inicio + 1h en vez de 1.5h — el inspector podía multar al
conductor con 30 minutos pagados aún.

Los datos existentes son todos enteros (siempre truncaron a entero) — la migración
de tipo es segura, no requiere backfill.
"""

from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app_estacionamiento", "0043_verificacioninspector_idx_vehiculo_fecha"),
    ]

    operations = [
        migrations.AlterField(
            model_name="estacionamiento",
            name="duracion_horas",
            field=models.DecimalField(
                max_digits=4,
                decimal_places=1,
                default=1,
                verbose_name="Duración (horas)",
            ),
        ),
    ]
