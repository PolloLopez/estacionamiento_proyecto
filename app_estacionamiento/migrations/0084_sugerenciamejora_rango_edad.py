from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app_estacionamiento", "0083_indices_infraccion_movcaja_cierre"),
    ]

    operations = [
        migrations.AddField(
            model_name="sugerenciamejora",
            name="rango_edad",
            field=models.CharField(
                blank=True,
                choices=[
                    ("menor18", "Menor de 18"),
                    ("18-25",   "18–25"),
                    ("26-35",   "26–35"),
                    ("36-50",   "36–50"),
                    ("51-65",   "51–65"),
                    ("mayor65", "Mayor de 65"),
                ],
                default="",
                max_length=10,
                verbose_name="Rango de edad",
            ),
        ),
    ]
