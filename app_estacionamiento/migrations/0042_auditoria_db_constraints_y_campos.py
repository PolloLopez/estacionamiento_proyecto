"""
Migración 0042 — Auditoría de base de datos (2026-07-24)

Cambios:
  1. Subcuadra.unique_together: ("calle","altura") → ("municipio","calle","altura")
     Corrige bug multi-tenancy: dos municipios ya pueden tener la misma calle+altura.

  2. on_delete CASCADE → PROTECT en modelos con historial contable:
     - Usuario.municipio (borrar municipio ya no borra sus usuarios)
     - Infraccion.inspector (borrar inspector ya no borra sus infracciones)
     - Infraccion.vehiculo (borrar vehículo ya no borra sus infracciones)
     - MovimientoCaja.usuario (borrar usuario ya no borra su historial de caja)
     - CierreCaja.usuario (ídem)

  3. Infraccion.municipio: CASCADE → SET_NULL
     (el municipio puede borrarse; la infracción queda sin municipio, no se destruye)

  4. Remover Municipio.apellido — campo muerto desde migración 0003.

  5. Remover Infraccion.qr_code — campo muerto desde migración 0008.

  6. MovimientoCaja.tipo: agregar choices=TIPOS (sin migración de datos, solo metadata).

  7. VerificacionInspector.resultado: agregar choices + default="verificado".

Ninguno de estos cambios requiere backfill de datos existentes.
Los cambios de on_delete solo afectan el comportamiento al intentar borrar; no tocan filas existentes.
"""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("app_estacionamiento", "0041_destinatarioinforme"),
    ]

    operations = [

        # ── 1. Subcuadra: agregar municipio al unique_together ────────────────
        migrations.AlterUniqueTogether(
            name="subcuadra",
            unique_together={("municipio", "calle", "altura")},
        ),

        # ── 2 & 3. Infraccion: on_delete en inspector, vehiculo y municipio ───
        migrations.AlterField(
            model_name="infraccion",
            name="inspector",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                to="app_estacionamiento.usuario",
            ),
        ),
        migrations.AlterField(
            model_name="infraccion",
            name="vehiculo",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                to="app_estacionamiento.vehiculo",
            ),
        ),
        migrations.AlterField(
            model_name="infraccion",
            name="municipio",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="app_estacionamiento.municipio",
            ),
        ),

        # ── 4. MovimientoCaja: on_delete + choices en tipo ───────────────────
        migrations.AlterField(
            model_name="movimientocaja",
            name="usuario",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                to="app_estacionamiento.usuario",
            ),
        ),
        migrations.AlterField(
            model_name="movimientocaja",
            name="tipo",
            field=models.CharField(
                choices=[("ingreso", "Ingreso"), ("egreso", "Egreso")],
                max_length=10,
            ),
        ),

        # ── 5. CierreCaja: on_delete ──────────────────────────────────────────
        migrations.AlterField(
            model_name="cierrecaja",
            name="usuario",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                to="app_estacionamiento.usuario",
            ),
        ),

        # ── 6. Usuario.municipio: on_delete ───────────────────────────────────
        migrations.AlterField(
            model_name="usuario",
            name="municipio",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="app_estacionamiento.municipio",
            ),
        ),

        # ── 7. Remover Municipio.apellido (campo muerto) ──────────────────────
        migrations.RemoveField(
            model_name="municipio",
            name="apellido",
        ),

        # ── 8. Remover Infraccion.qr_code (campo muerto) ─────────────────────
        migrations.RemoveField(
            model_name="infraccion",
            name="qr_code",
        ),

        # ── 9. VerificacionInspector.resultado: agregar choices + default ─────
        migrations.AlterField(
            model_name="verificacioninspector",
            name="resultado",
            field=models.CharField(
                choices=[("verificado", "Verificado")],
                default="verificado",
                max_length=50,
            ),
        ),
    ]
