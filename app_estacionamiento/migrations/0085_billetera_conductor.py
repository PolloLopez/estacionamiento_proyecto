# Migración manual — 2026-09-20
# Crea BilleteraConductor: saldo del conductor aislado por municipio.
# Reemplaza el uso de Usuario.saldo para el flujo del conductor.
# Usuario.saldo se mantiene como campo legacy para retrocompatibilidad.

from decimal import Decimal
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app_estacionamiento", "0084_sugerenciamejora_rango_edad"),
    ]

    operations = [
        migrations.CreateModel(
            name="BilleteraConductor",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "saldo",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("0"),
                        max_digits=10,
                        verbose_name="Saldo disponible",
                    ),
                ),
                (
                    "conductor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="billeteras",
                        to="app_estacionamiento.usuario",
                        verbose_name="Conductor",
                    ),
                ),
                (
                    "municipio",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="billeteras",
                        to="app_estacionamiento.municipio",
                        verbose_name="Municipio",
                    ),
                ),
            ],
            options={
                "verbose_name": "Billetera del conductor",
                "verbose_name_plural": "Billeteras de conductores",
            },
        ),
        migrations.AddConstraint(
            model_name="billeteraconductor",
            constraint=models.UniqueConstraint(
                fields=["conductor", "municipio"],
                name="unique_billetera_conductor_municipio",
            ),
        ),
    ]
