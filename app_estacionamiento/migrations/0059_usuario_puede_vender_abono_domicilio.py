# Migración manual — 2026-09-01
# Agrega:
#   - puede_vender_abono (BooleanField) en Usuario: permiso individual para cobrar abonos
#   - domicilio (CharField) en Usuario: dirección del conductor (frentistas, reintegro)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_estacionamiento', '0058_sia_titular_fields_vehiculo'),
    ]

    operations = [
        migrations.AddField(
            model_name='usuario',
            name='puede_vender_abono',
            field=models.BooleanField(
                default=True,
                help_text='Si está deshabilitado, el vendedor no verá la opción de cobrar abono.',
                verbose_name='Puede vender abono mensual',
            ),
        ),
        migrations.AddField(
            model_name='usuario',
            name='domicilio',
            field=models.CharField(
                blank=True,
                default='',
                max_length=255,
                verbose_name='Domicilio',
                help_text='Dirección del conductor. Requerido para exención de frentista.',
            ),
        ),
    ]
