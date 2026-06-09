"""
Migración 0026 — Creada manualmente (Django no disponible en sandbox)

Cambios:
  - Vehiculo: agrega tipo_exencion, notas_exencion
  - Nuevo modelo HorarioEstacionamiento
  - Nuevo modelo DiaEspecial
"""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("app_estacionamiento", "0025_usuario_rendicion_config"),
    ]

    operations = [

        # ─── Vehiculo: tipo de exención y notas ───────────────────
        migrations.AddField(
            model_name="vehiculo",
            name="tipo_exencion",
            field=models.CharField(
                blank=True,
                choices=[
                    ("discapacitado", "Discapacitado"),
                    ("vecino_frentista", "Vecino frentista"),
                    ("jubilado", "Jubilado"),
                    ("fuerza", "Fuerzas de seguridad / Policía"),
                    ("vehiculo_oficial", "Vehículo oficial"),
                ],
                max_length=30,
                null=True,
                verbose_name="Tipo de exención",
            ),
        ),
        migrations.AddField(
            model_name="vehiculo",
            name="notas_exencion",
            field=models.TextField(
                blank=True,
                null=True,
                verbose_name="Notas (nro de documento, certificado, etc.)",
            ),
        ),

        # ─── HorarioEstacionamiento ────────────────────────────────
        migrations.CreateModel(
            name="HorarioEstacionamiento",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("dia_semana", models.IntegerField(
                    choices=[
                        (0, "Lunes"), (1, "Martes"), (2, "Miércoles"),
                        (3, "Jueves"), (4, "Viernes"), (5, "Sábado"), (6, "Domingo"),
                    ]
                )),
                ("hora_inicio", models.TimeField()),
                ("hora_fin", models.TimeField()),
                ("activo", models.BooleanField(default=True)),
                ("municipio", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    to="app_estacionamiento.municipio",
                )),
            ],
            options={
                "ordering": ["dia_semana"],
                "unique_together": {("municipio", "dia_semana")},
            },
        ),

        # ─── DiaEspecial ───────────────────────────────────────────
        migrations.CreateModel(
            name="DiaEspecial",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("fecha", models.DateField()),
                ("tipo", models.CharField(
                    choices=[
                        ("feriado", "Feriado nacional"),
                        ("festivo", "Festivo local"),
                        ("duelo", "Duelo / Luto"),
                        ("otro", "Otro"),
                    ],
                    default="feriado",
                    max_length=20,
                )),
                ("descripcion", models.CharField(max_length=200)),
                ("cobro_activo", models.BooleanField(
                    default=False,
                    help_text="Por defecto los días especiales son libres de cobro.",
                    verbose_name="¿Se cobra ese día?",
                )),
                ("municipio", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    to="app_estacionamiento.municipio",
                )),
            ],
            options={
                "ordering": ["fecha"],
                "unique_together": {("municipio", "fecha")},
            },
        ),
    ]
