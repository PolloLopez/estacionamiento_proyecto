from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_estacionamiento', '0072_alter_liquidacionplataforma_id_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='usuario',
            name='puede_cobrar_infraccion',
            field=models.BooleanField(
                default=True,
                help_text='Si está deshabilitado, el vendedor no verá la opción de cobrar infracciones.',
                verbose_name='Puede cobrar infracciones',
            ),
        ),
    ]
