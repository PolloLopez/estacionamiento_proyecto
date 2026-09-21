from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_estacionamiento', '0086_municipio_modulo_informes_activo'),
    ]

    operations = [
        migrations.AddField(
            model_name='municipio',
            name='puede_gestionar_subcuadras',
            field=models.BooleanField(
                default=False,
                verbose_name='Admin puede gestionar subcuadras',
                help_text=(
                    'Si está activo, el admin municipal puede crear, editar y asignar '
                    'coordenadas GPS a las subcuadras desde /admin-subcuadras/. '
                    'Por defecto solo el superadmin puede hacerlo.'
                ),
            ),
        ),
    ]
