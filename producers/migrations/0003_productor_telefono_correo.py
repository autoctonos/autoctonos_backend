from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("productores", "0002_remove_municipio_id_departamento_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="productor",
            name="telefono",
            field=models.CharField(blank=False, default="", max_length=20, verbose_name="Teléfono"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="productor",
            name="correo",
            field=models.EmailField(blank=True, null=True, verbose_name="Correo Electrónico"),
        ),
    ]
