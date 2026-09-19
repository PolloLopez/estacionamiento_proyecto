from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_estacionamiento', '0078_alter_municipio_inspector_ve_sus_infracciones_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='municipio',
            name='admin_puede_editar_plantillas',
            field=models.BooleanField(
                default=False,
                verbose_name='Admin puede editar plantillas de comprobantes',
                help_text=(
                    'Si está activo, el admin municipal puede editar los textos de '
                    'encabezado/cuerpo/pie de los comprobantes de su municipio. '
                    'Por defecto solo el superadmin puede hacerlo.'
                ),
            ),
        ),
    ]
